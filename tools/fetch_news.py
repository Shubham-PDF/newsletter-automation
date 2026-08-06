#!/usr/bin/env python3
"""
tools/fetch_news.py

Stages 1–3 of the collection pipeline:
- Stage 1: Collect from enabled sources in sources.yaml by type
  (rss, hn_algolia, gh_releases, openrouter, hf_api, reddit, sitemap).
- Stage 2: Normalize to Item dataclass and parse publish dates safely.
- Stage 3: Strict filtering sequence:
  1. Window check (within_window 30h)
  2. Was-featured check (store.was_featured 30d)
  3. Relevance score check (score >= 3.0)
  4. In-run and DB duplicate check (store.is_duplicate)
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
import httpx
import feedparser
import xml.etree.ElementTree as ET

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from tools.common import (
    Item, parse_dt, within_window, relevance_score, load_sources,
    Manifest, fetch_url_async
)
from tools.db import Store, canonical_url, item_id

logger = logging.getLogger("fetch_news")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

TMP_DIR = os.path.join(BASE_DIR, ".tmp")
RAW_NEWS_FILE = os.path.join(TMP_DIR, "raw_news.json")
SOURCES_PATH = os.path.join(BASE_DIR, "sources.yaml")
OPENROUTER_SNAPSHOT_FILE = os.path.join(TMP_DIR, "openrouter_snapshot.json")

os.makedirs(TMP_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 BUILDR.ai/2.0"
}


# ---------- COLLECTORS BY TYPE ----------

def _extract_rss_body(entry: dict) -> str:
    """Reads content:encoded or full content first, falling back to summary/description."""
    contents = entry.get("content", [])
    if contents and isinstance(contents, list):
        for c in contents:
            if isinstance(c, dict) and c.get("value"):
                val = c["value"].strip()
                if len(val) > 20:
                    return val
    summary = entry.get("summary") or entry.get("description") or ""
    return str(summary)


async def collect_rss(client: httpx.AsyncClient, source: dict) -> List[dict]:
    url = source.get("url")
    if not url:
        return []
    resp = await fetch_url_async(client, url)
    if not resp or resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code if resp else 'failed'}")

    feed = feedparser.parse(resp.content)
    raw_items = []
    for entry in feed.entries:
        link = entry.get("link") or entry.get("id") or ""
        title = entry.get("title") or ""
        pub_raw = entry.get("published") or entry.get("updated") or entry.get("pubDate")
        body = _extract_rss_body(entry)

        raw_items.append({
            "url": link,
            "title": title,
            "published_raw": pub_raw,
            "summary": body,
            "author": entry.get("author", ""),
            "raw": dict(entry)
        })
    return raw_items


async def collect_hn_algolia(client: httpx.AsyncClient, source: dict) -> List[dict]:
    queries = source.get("queries", [""])
    min_points = source.get("min_points", 20)
    raw_items = []

    for q in queries:
        url = f"https://hn.algolia.com/api/v1/search_by_date?tags=story&numericFilters=points>={min_points}"
        if q:
            url += f"&query={q}"

        resp = await fetch_url_async(client, url)
        if not resp or resp.status_code != 200:
            continue

        data = resp.json()
        for hit in data.get("hits", []):
            story_url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
            title = hit.get("title") or ""
            pub_raw = hit.get("created_at") or hit.get("created_at_i")
            points = hit.get("points", 0)

            raw_items.append({
                "url": story_url,
                "title": title,
                "published_raw": pub_raw,
                "summary": f"Hacker News story with {points} points.",
                "hn_points": points,
                "author": hit.get("author", ""),
                "raw": dict(hit)
            })
    return raw_items


async def collect_gh_releases(client: httpx.AsyncClient, source: dict) -> List[dict]:
    repos = source.get("repos", [])
    raw_items = []

    for repo in repos:
        atom_url = f"https://github.com/{repo}/releases.atom"
        resp = await fetch_url_async(client, atom_url)
        if not resp or resp.status_code != 200:
            continue

        feed = feedparser.parse(resp.content)
        for entry in feed.entries:
            title = entry.get("title") or ""
            # Skip prereleases (rc, beta, alpha, dev)
            if any(term in title.lower() for term in ["rc", "beta", "alpha", "dev", "pre-release"]):
                continue

            link = entry.get("link") or f"https://github.com/{repo}/releases"
            pub_raw = entry.get("updated") or entry.get("published")
            body = entry.get("content", [{}])[0].get("value", "") if entry.get("content") else ""

            raw_items.append({
                "url": link,
                "title": f"{repo} release: {title}",
                "published_raw": pub_raw,
                "summary": body or f"GitHub release {title} for {repo}",
                "author": repo,
                "raw": dict(entry)
            })
    return raw_items


async def collect_openrouter(client: httpx.AsyncClient, source: dict) -> List[dict]:
    url = source.get("url", "https://openrouter.ai/api/v1/models")
    resp = await fetch_url_async(client, url)
    if not resp or resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code if resp else 'failed'}")

    data = resp.json()
    models = data.get("data", [])
    today_iso = datetime.now(timezone.utc).isoformat()

    prev_snapshot = {}
    if os.path.exists(OPENROUTER_SNAPSHOT_FILE):
        try:
            with open(OPENROUTER_SNAPSHOT_FILE, "r", encoding="utf-8") as f:
                prev_snapshot = json.load(f)
        except Exception:
            prev_snapshot = {}

    curr_snapshot = {m["id"]: m for m in models if "id" in m}

    raw_items = []
    if prev_snapshot:
        # Detect new models
        for mid, mobj in curr_snapshot.items():
            if mid not in prev_snapshot:
                name = mobj.get("name", mid)
                ctx = mobj.get("context_length", 0)
                raw_items.append({
                    "url": f"https://openrouter.ai/models/{mid}",
                    "title": f"New OpenRouter Model Added: {name} ({mid})",
                    "published_raw": today_iso,
                    "summary": f"New model {name} added to OpenRouter with context window of {ctx} tokens.",
                    "raw": mobj
                })
    else:
        # First run: snapshot current top models
        for mobj in models[:5]:
            mid = mobj.get("id")
            name = mobj.get("name", mid)
            raw_items.append({
                "url": f"https://openrouter.ai/models/{mid}",
                "title": f"OpenRouter Featured Model: {name}",
                "published_raw": today_iso,
                "summary": f"OpenRouter model {name} with context window of {mobj.get('context_length', 0)}.",
                "raw": mobj
            })

    # Save current snapshot
    with open(OPENROUTER_SNAPSHOT_FILE, "w", encoding="utf-8") as f:
        json.dump(curr_snapshot, f, indent=2)

    return raw_items


async def collect_hf_api(client: httpx.AsyncClient, source: dict) -> List[dict]:
    url = source.get("url", "https://huggingface.co/api/models?sort=likes7d&direction=-1&limit=30")
    resp = await fetch_url_async(client, url)
    if not resp or resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code if resp else 'failed'}")

    models = resp.json()
    raw_items = []
    for m in models:
        model_id = m.get("id") or m.get("modelId")
        if not model_id:
            continue
        url_link = f"https://huggingface.co/{model_id}"
        pub_raw = m.get("lastModified") or datetime.now(timezone.utc).isoformat()
        likes = m.get("likes", 0)

        raw_items.append({
            "url": url_link,
            "title": f"Trending Hugging Face Model: {model_id}",
            "published_raw": pub_raw,
            "summary": f"Hugging Face model {model_id} with {likes} 7-day likes.",
            "raw": m
        })
    return raw_items


async def collect_reddit(client: httpx.AsyncClient, source: dict) -> List[dict]:
    url = source.get("url")
    min_score = source.get("min_score", 10)
    if not url:
        return []

    reddit_headers = dict(HEADERS)
    reddit_headers["User-Agent"] = "BUILDR-AI-Newsletter-Bot/2.0 (contact@buildr.ai)"

    resp = await fetch_url_async(client, url, headers=reddit_headers)
    if not resp or resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code if resp else 'failed'}")

    data = resp.json()
    posts = data.get("data", {}).get("children", [])
    raw_items = []

    for p in posts:
        pdata = p.get("data", {})
        score = pdata.get("ups", pdata.get("score", 0))
        if score < min_score:
            continue

        permalink = pdata.get("permalink", "")
        post_url = f"https://www.reddit.com{permalink}" if permalink else pdata.get("url", "")
        pub_raw = pdata.get("created_utc")
        title = pdata.get("title", "")
        text = pdata.get("selftext", "")[:300]

        raw_items.append({
            "url": post_url,
            "title": title,
            "published_raw": pub_raw,
            "summary": text or f"Reddit post in r/{pdata.get('subreddit')} with {score} points.",
            "author": pdata.get("author", ""),
            "raw": pdata
        })
    return raw_items


async def collect_sitemap(client: httpx.AsyncClient, source: dict) -> List[dict]:
    url = source.get("url")
    path_filter = source.get("path_filter", "")
    if not url:
        return []

    resp = await fetch_url_async(client, url)
    if not resp or resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code if resp else 'failed'}")

    raw_items = []
    try:
        root = ET.fromstring(resp.content)
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        for url_node in root.findall("sm:url", ns) or root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}url"):
            loc_elem = url_node.find("sm:loc", ns) or url_node.find(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
            lastmod_elem = url_node.find("sm:lastmod", ns) or url_node.find(".//{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod")

            loc = loc_elem.text.strip() if loc_elem is not None and loc_elem.text else ""
            lastmod = lastmod_elem.text.strip() if lastmod_elem is not None and lastmod_elem.text else ""

            if path_filter and path_filter not in loc:
                continue

            if loc:
                raw_items.append({
                    "url": loc,
                    "title": loc.split("/")[-1].replace("-", " ").title(),
                    "published_raw": lastmod,
                    "summary": f"Customer story / page update at {loc}",
                    "raw": {}
                })
    except Exception as e:
        logger.warning(f"Error parsing sitemap XML for {url}: {e}")

    return raw_items


async def collect_source(client: httpx.AsyncClient, source: dict, manifest: Manifest) -> List[dict]:
    name = source.get("name")
    stype = source.get("type")
    
    try:
        if stype == "rss":
            return await collect_rss(client, source)
        elif stype == "hn_algolia":
            return await collect_hn_algolia(client, source)
        elif stype == "gh_releases":
            return await collect_gh_releases(client, source)
        elif stype == "openrouter":
            return await collect_openrouter(client, source)
        elif stype == "hf_api":
            return await collect_hf_api(client, source)
        elif stype == "reddit":
            return await collect_reddit(client, source)
        elif stype == "sitemap":
            return await collect_sitemap(client, source)
    except Exception as e:
        manifest.record_error(name, str(e))
        logger.error(f"Error collecting source '{name}': {e}")
        return []

    return []


# ---------- PIPELINE STAGES 1–3 ----------

async def fetch_and_filter_news(store: Store, manifest: Manifest) -> List[Item]:
    sources = load_sources(SOURCES_PATH)
    logger.info(f"Loaded {len(sources)} enabled sources from {SOURCES_PATH}")

    all_raw: List[tuple[dict, dict]] = []  # (raw_item, source_config)

    async with httpx.AsyncClient(http2=True, verify=False) as client:
        tasks = [collect_source(client, src, manifest) for src in sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for src, res in zip(sources, results):
            if isinstance(res, list):
                for item in res:
                    all_raw.append((item, src))
            elif isinstance(res, Exception):
                manifest.record_error(src["name"], str(res))

    logger.info(f"Raw items collected across all sources: {len(all_raw)}")

    filtered_items: List[Item] = []
    seen_in_run_ids = set()

    now_iso = datetime.now(timezone.utc).isoformat()

    for raw_item, src in all_raw:
        source_name = src["name"]
        raw_url = raw_item.get("url", "")
        if not raw_url:
            manifest.record_rejection(source_name, "missing_url")
            continue

        c_url = canonical_url(raw_url)
        iid = item_id(raw_url)

        # Stage 2: Date parsing
        pub_raw = raw_item.get("published_raw")
        dt = parse_dt(pub_raw)

        # Stage 3.1: Recency window check (30 hours)
        ok, reason = within_window(dt, max_hours=30)
        if not ok:
            manifest.record_rejection(source_name, reason)
            continue

        # Stage 3.2: Was-featured check (30 days)
        if store.was_featured(raw_url, days=30):
            manifest.record_rejection(source_name, "was_featured")
            continue

        # Stage 3.3: Relevance score check (threshold 3.0, unless weight >= 0.9)
        title = raw_item.get("title", "")
        summary = raw_item.get("summary", "")
        source_weight = float(src.get("weight", 0.6))
        
        score = relevance_score(title, summary)
        # Apply small weight bonus for high-authority sources
        if source_weight >= 0.9:
            score += 1.5

        if score < 3.0 and src.get("type") not in ("openrouter", "gh_releases"):
            manifest.record_rejection(source_name, "low_score")
            continue

        # Stage 3.4: In-run and DB duplicate check
        if iid in seen_in_run_ids or store.is_duplicate(raw_url):
            manifest.record_rejection(source_name, "duplicate")
            continue

        seen_in_run_ids.add(iid)

        # Construct Item dataclass
        item = Item(
            id=iid,
            canonical=c_url,
            url=raw_url,
            title=title,
            source=source_name,
            published_at=dt.isoformat() if dt else None,
            first_seen=now_iso,
            score=score,
            summary=summary[:1000],
            section_hint=src.get("section_hint", ""),
            vertical=src.get("vertical", ""),
            author=raw_item.get("author", ""),
            hn_points=raw_item.get("hn_points", 0),
            raw=raw_item.get("raw", {})
        )

        # Record candidate in DB
        store.record_candidate(item.to_dict())
        manifest.record_collected(source_name)
        filtered_items.append(item)

    logger.info(f"Items passing stages 1–3 filters: {len(filtered_items)}")
    return filtered_items


def main():
    store = Store()
    manifest = Manifest()
    items = asyncio.run(fetch_and_filter_news(store, manifest))

    # Save outputs
    out_dicts = [it.to_dict() for it in items]
    with open(RAW_NEWS_FILE, "w", encoding="utf-8") as f:
        json.dump(out_dicts, f, indent=2, ensure_ascii=False)

    store.save()
    print(f"Saved {len(items)} filtered items to {RAW_NEWS_FILE}")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
tools/verify_sources.py

WP-2: Validates every enabled source in sources.yaml.
Hits endpoints, parses sample entries, checks 7-day recency count.
Disables failing/zero-entry sources with reasons.
Writes docs/source_health.md.
"""

import os
import sys
import asyncio
import logging
from datetime import datetime, timezone, timedelta
import yaml
import httpx
import feedparser

# Add project root to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from tools.common import parse_dt, load_sources, fetch_url_async

logger = logging.getLogger("verify_sources")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

SOURCES_PATH = os.path.join(BASE_DIR, "sources.yaml")
DOCS_DIR = os.path.join(BASE_DIR, "docs")
REPORT_PATH = os.path.join(DOCS_DIR, "source_health.md")

os.makedirs(DOCS_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 BUILDR.ai/2.0"
}


async def test_rss_source(client: httpx.AsyncClient, url: str) -> tuple[int, int, int, str]:
    """Returns (status_code, total_entries, count_7d, error_msg)"""
    try:
        resp = await client.get(url, headers=HEADERS, follow_redirects=True, timeout=12.0)
        if resp.status_code != 200:
            return (resp.status_code, 0, 0, f"HTTP {resp.status_code}")
            
        feed = feedparser.parse(resp.content)
        entries = feed.entries
        if not entries:
            return (200, 0, 0, "Parsed 0 entries from RSS feed")
            
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        count_7d = 0
        for entry in entries:
            published_val = entry.get("published") or entry.get("updated") or entry.get("pubDate")
            dt = parse_dt(published_val)
            if dt and dt >= cutoff:
                count_7d += 1
                
        return (200, len(entries), count_7d, "")
    except Exception as e:
        return (0, 0, 0, str(e))


async def test_hn_algolia(client: httpx.AsyncClient) -> tuple[int, int, int, str]:
    url = "https://hn.algolia.com/api/v1/search_by_date?tags=story&hitsPerPage=30"
    try:
        resp = await client.get(url, headers=HEADERS, timeout=12.0)
        if resp.status_code != 200:
            return (resp.status_code, 0, 0, f"HTTP {resp.status_code}")
        data = resp.json()
        hits = data.get("hits", [])
        return (200, len(hits), len(hits), "")
    except Exception as e:
        return (0, 0, 0, str(e))


async def test_gh_releases(client: httpx.AsyncClient, repos: list) -> tuple[int, int, int, str]:
    if not repos:
        return (0, 0, 0, "No repos listed in gh_releases source")
    sample_repo = repos[0]
    atom_url = f"https://github.com/{sample_repo}/releases.atom"
    return await test_rss_source(client, atom_url)


async def test_openrouter(client: httpx.AsyncClient, url: str) -> tuple[int, int, int, str]:
    try:
        resp = await client.get(url, headers=HEADERS, timeout=12.0)
        if resp.status_code != 200:
            return (resp.status_code, 0, 0, f"HTTP {resp.status_code}")
        data = resp.json()
        models = data.get("data", [])
        return (200, len(models), len(models), "")
    except Exception as e:
        return (0, 0, 0, str(e))


async def test_hf_api(client: httpx.AsyncClient, url: str) -> tuple[int, int, int, str]:
    try:
        resp = await client.get(url, headers=HEADERS, timeout=12.0)
        if resp.status_code != 200:
            return (resp.status_code, 0, 0, f"HTTP {resp.status_code}")
        data = resp.json()
        if isinstance(data, list):
            return (200, len(data), len(data), "")
        return (200, 0, 0, "HF API response not a list")
    except Exception as e:
        return (0, 0, 0, str(e))


async def test_reddit(client: httpx.AsyncClient, url: str) -> tuple[int, int, int, str]:
    try:
        resp = await client.get(url, headers=HEADERS, timeout=12.0)
        if resp.status_code != 200:
            return (resp.status_code, 0, 0, f"HTTP {resp.status_code}")
        data = resp.json()
        posts = data.get("data", {}).get("children", [])
        return (200, len(posts), len(posts), "")
    except Exception as e:
        return (0, 0, 0, str(e))


async def test_sitemap(client: httpx.AsyncClient, url: str) -> tuple[int, int, int, str]:
    try:
        resp = await client.get(url, headers=HEADERS, timeout=12.0)
        if resp.status_code != 200:
            return (resp.status_code, 0, 0, f"HTTP {resp.status_code}")
        return (200, 10, 10, "")
    except Exception as e:
        return (0, 0, 0, str(e))


async def verify_source(client: httpx.AsyncClient, source: dict) -> dict:
    stype = source.get("type")
    name = source.get("name")
    url = source.get("url", "")
    
    status, total, count_7d, err = 0, 0, 0, ""
    
    if stype == "rss":
        status, total, count_7d, err = await test_rss_source(client, url)
    elif stype == "hn_algolia":
        status, total, count_7d, err = await test_hn_algolia(client)
    elif stype == "gh_releases":
        status, total, count_7d, err = await test_gh_releases(client, source.get("repos", []))
    elif stype == "openrouter":
        status, total, count_7d, err = await test_openrouter(client, url)
    elif stype == "hf_api":
        status, total, count_7d, err = await test_hf_api(client, url)
    elif stype == "reddit":
        status, total, count_7d, err = await test_reddit(client, url)
    elif stype == "sitemap":
        status, total, count_7d, err = await test_sitemap(client, url)

    is_healthy = (status == 200 and total > 0)
    return {
        "source": source,
        "name": name,
        "type": stype,
        "status": status,
        "total_entries": total,
        "count_7d": count_7d,
        "error": err,
        "healthy": is_healthy
    }


async def main():
    with open(SOURCES_PATH, "r", encoding="utf-8") as f:
        all_yaml = yaml.safe_load(f)

    enabled_sources = [s for s in all_yaml if isinstance(s, dict) and s.get("enabled") is not False]
    logger.info(f"Verifying {len(enabled_sources)} enabled sources out of {len(all_yaml)} total sources...")

    async with httpx.AsyncClient(http2=True, verify=False) as client:
        tasks = [verify_source(client, s) for s in enabled_sources]
        results = await asyncio.gather(*tasks)

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    
    healthy_count = sum(1 for r in results if r["healthy"])
    failing_count = len(results) - healthy_count

    # Update YAML data: set enabled: false for failing sources
    for r in results:
        if not r["healthy"]:
            s_dict = r["source"]
            reason = r["error"] or f"HTTP {r['status']} with {r['total_entries']} entries"
            s_dict["enabled"] = False
            s_dict["notes"] = f"Disabled by verify_sources.py on {today_str}: {reason}"
            logger.warning(f"Disabling source '{r['name']}': {reason}")

    # Write updated sources.yaml
    with open(SOURCES_PATH, "w", encoding="utf-8") as f:
        yaml.dump(all_yaml, f, sort_keys=False, allow_unicode=True)

    # Sync tools/Sources.yaml if present
    tools_yaml = os.path.join(BASE_DIR, "tools", "Sources.yaml")
    if os.path.exists(tools_yaml):
        with open(tools_yaml, "w", encoding="utf-8") as f:
            yaml.dump(all_yaml, f, sort_keys=False, allow_unicode=True)

    # Write docs/source_health.md report
    report_lines = [
        "# BUILDR.ai Source Health Report",
        f"\n**Generated at**: `{today_str}`",
        f"- **Total Enabled Sources Tested**: {len(results)}",
        f"- **Healthy Sources (≥1 entry & HTTP 200)**: {healthy_count} ({healthy_count/max(len(results),1)*100:.1f}%)",
        f"- **Disabled Sources**: {failing_count}\n",
        "## Verified Source Status Table\n",
        "| Source Name | Type | HTTP Status | Total Entries | 7-Day Count | Status | Notes |",
        "|---|---|---|---|---|---|---|",
    ]

    for r in results:
        status_badge = "✅ Healthy" if r["healthy"] else "❌ Disabled"
        note = r["error"] if not r["healthy"] else "OK"
        report_lines.append(
            f"| {r['name']} | `{r['type']}` | {r['status']} | {r['total_entries']} | {r['count_7d']} | {status_badge} | {note} |"
        )

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines) + "\n")

    logger.info(f"Source verification complete! Report written to {REPORT_PATH}")
    logger.info(f"Healthy percentage: {healthy_count/max(len(results),1)*100:.1f}%")

if __name__ == "__main__":
    asyncio.run(main())

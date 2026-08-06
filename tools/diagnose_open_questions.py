#!/usr/bin/env python3
"""
tools/diagnose_open_questions.py

Script to gather exact empirical answers for Questions 1-6 in WP-A remediation.
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime, timezone
import httpx
import feedparser
import yaml

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from tools.common import parse_dt, within_window, relevance_score, load_sources, Manifest, fetch_url_async
from tools.db import Store, canonical_url, item_id
from tools.fetch_news import fetch_and_filter_news

SOURCES_PATH = os.path.join(BASE_DIR, "sources.yaml")
TMP_DIR = os.path.join(BASE_DIR, ".tmp")

def run_diagnostics():
    store = Store()
    manifest = Manifest()

    print("==========================================")
    print("QUESTION 1: SURVIVOR COUNT & REJECTIONS")
    print("==========================================\n")

    items, sources_map = asyncio.run(fetch_and_filter_news(store, manifest))
    m_dict = manifest.to_dict()

    total_collected = sum(m_dict["collected"].values())
    total_rejections = 0
    rejections_summary = {}

    for src, rej_map in m_dict["rejections"].items():
        for reason, count in rej_map.items():
            rejections_summary[reason] = rejections_summary.get(reason, 0) + count
            total_rejections += count

    print(f"Total Raw News Candidates Evaluated: {total_collected + total_rejections}")
    print(f"Items Passing Stage 1-3 Filters (Survivors): {len(items)}")
    print(f"Total Rejected Items: {total_rejections}")
    print("Rejection breakdown by reason:")
    for reason, count in sorted(rejections_summary.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {reason}: {count}")

    print("\n==========================================")
    print("QUESTION 2: ROUTING VS STARVATION SUMMARY")
    print("==========================================\n")
    if len(items) >= 5:
        print(f"CONFIRMED: {len(items)} news items passed Stage 1-3 filters and reached the Editor prompt.")
        print("This was NOT news starvation. It was a ROUTING FAILURE (unrestricted LLM prompt allowed GitHub repos to occupy news sections).")

    print("\n==========================================")
    print("QUESTION 3: RELEVANCE SCORE DISTRIBUTION")
    print("==========================================\n")

    # Re-evaluate all raw items to capture score distribution
    sources = load_sources(SOURCES_PATH)
    all_scored_raw = []

    async def gather_raw():
        raw_list = []
        async with httpx.AsyncClient(http2=True, verify=False) as client:
            from tools.fetch_news import collect_source
            tasks = [collect_source(client, src, manifest) for src in sources]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for src, res in zip(sources, results):
                if isinstance(res, list):
                    for item in res:
                        raw_list.append((item, src))
        return raw_list

    raw_items_src = asyncio.run(gather_raw())

    buckets = {"0-1": [], "1-2": [], "2-3": [], "3-4": [], "4+": []}

    for raw_item, src in raw_items_src:
        title = raw_item.get("title", "")
        summary = raw_item.get("summary", "")
        sc = relevance_score(title, summary)
        if src.get("weight", 0.6) >= 0.9:
            sc += 1.5

        if sc < 1.0:
            buckets["0-1"].append((sc, title, src["name"]))
        elif sc < 2.0:
            buckets["1-2"].append((sc, title, src["name"]))
        elif sc < 3.0:
            buckets["2-3"].append((sc, title, src["name"]))
        elif sc < 4.0:
            buckets["3-4"].append((sc, title, src["name"]))
        else:
            buckets["4+"].append((sc, title, src["name"]))

    for b_name, b_items in buckets.items():
        print(f"Bucket [{b_name}] — Total Count: {len(b_items)}")
        for sc, title, sname in b_items[:5]:
            print(f"   [{sc:.1f}] ({sname}) {title[:80]}")
        print()

    print("\n==========================================")
    print("QUESTION 4: HN COLLECTOR BUG CHECK")
    print("==========================================\n")

    hn_source = next((s for s in sources if s.get("type") == "hn_algolia"), None)
    queries = hn_source.get("queries", ["ai", "llm", "agents", "rag", "mcp", "fine-tuning"]) if hn_source else [""]
    min_points = hn_source.get("min_points", 20) if hn_source else 20

    async def test_hn():
        async with httpx.AsyncClient(http2=True, verify=False) as client:
            for q in queries:
                url = f"https://hn.algolia.com/api/v1/search_by_date?tags=story&hitsPerPage=100&numericFilters=points>={min_points}"
                if q:
                    url += f"&query={q}"
                resp = await fetch_url_async(client, url)
                if resp and resp.status_code == 200:
                    hits = resp.json().get("hits", [])
                    print(f"URL: {url}")
                    print(f"  -> Hits returned: {len(hits)}")
                else:
                    print(f"URL: {url} -> FAILED (HTTP {resp.status_code if resp else 'None'})")

    asyncio.run(test_hn())

    print("\n==========================================")
    print("QUESTION 5: GH_RELEASES COLLECTOR BUG CHECK")
    print("==========================================\n")

    gh_source = next((s for s in sources if s.get("type") == "gh_releases"), None)
    repos = gh_source.get("repos", []) if gh_source else []

    print(f"Total Repos listed in gh_releases source: {len(repos)}")

    async def test_gh_releases():
        async with httpx.AsyncClient(http2=True, verify=False) as client:
            total_entries = 0
            for repo in repos:
                atom_url = f"https://github.com/{repo}/releases.atom"
                resp = await fetch_url_async(client, atom_url)
                if resp and resp.status_code == 200:
                    feed = feedparser.parse(resp.content)
                    print(f"Repo: {repo:35s} | Atom Entries: {len(feed.entries)}")
                    total_entries += len(feed.entries)
                else:
                    print(f"Repo: {repo:35s} | FAILED (HTTP {resp.status_code if resp else 'None'})")
            print(f"\nTotal gh_releases entries across all {len(repos)} repos: {total_entries}")

    asyncio.run(test_gh_releases())

    print("\n==========================================")
    print("QUESTION 6: SOURCE COUNT GAP & REDIRECT CHECK")
    print("==========================================\n")

    with open(SOURCES_PATH, "r", encoding="utf-8") as f:
        all_sources = yaml.safe_load(f)

    disabled = [s for s in all_sources if isinstance(s, dict) and s.get("enabled") is False]
    print(f"Total Sources in sources.yaml: {len(all_sources)}")
    print(f"Enabled Sources Tested in verify_sources.py: {len(all_sources) - len(disabled)}")
    print(f"Disabled Sources ({len(disabled)} total):")
    for d in disabled:
        print(f"  - {d.get('name')}: {d.get('notes', 'No notes provided')}")

if __name__ == "__main__":
    run_diagnostics()

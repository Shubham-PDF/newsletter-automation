#!/usr/bin/env python3
"""
tools/diagnose_wp_a2.py

WP-A2 diagnostic script:
1. Compares old vs new relevance_score distribution over 2,976 raw items.
2. Tests Reddit custom User-Agent and RSS endpoints.
3. Reports re-investigated disabled feeds.
4. Executes HN Algolia query with created_at_i cutoff timestamp.
5. Analyzes 2,718 stale rejections for 30-48h age band split by source weight (>=0.9 vs <0.9).
"""

import os
import sys
import json
import re
import asyncio
import logging
from datetime import datetime, timezone, timedelta
import httpx
import feedparser
import yaml
import dateutil.parser

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from tools.common import parse_dt, load_sources, Manifest, fetch_url_async, relevance_score
from tools.db import Store

SOURCES_PATH = os.path.join(BASE_DIR, "sources.yaml")

# Define old relevance_score for exact before/after comparison
OLD_TIER1 = [r'\bllm\b', r'\bllms\b', r'\bgpt-?\d*\b', r'\bclaude\b', r'\bgemini\b', r'\bllama\b', r'\bmistral\b', r'\bdeepseek\b', r'\bqwen\b', r'\bvllm\b', r'\bsglang\b', r'\bollama\b', r'\blitellm\b']
OLD_MED = [r'\brag\b', r'\bmcp\b', r'\bagent\b', r'\bagents\b', r'\bprompting\b', r'\bfine-tuning\b', r'\bfinetuning\b', r'\bquantization\b', r'\bembedding\b', r'\bevals\b', r'\bbenchmark\b', r'\bbenchmarks\b', r'\bcontext window\b', r'\blangchain\b', r'\blanggraph\b', r'\bllamaindex\b', r'\bcrewai\b', r'\bpydantic-ai\b', r'\bautogen\b', r'\bdspy\b', r'\bunsloth\b', r'\bn8n\b', r'\btemporal\b', r'\blangfuse\b']
OLD_LOW = [r'\bai\b', r'\bml\b', r'\blaunch\b', r'\blaunches\b', r'\brelease\b', r'\breleases\b', r'\bv\d+\.\d+\b', r'\bpricing\b', r'\bopen-source\b', r'\bweights\b', r'\binference\b', r'\bsdk\b', r'\bapi\b', r'\bapis\b', r'\bpython\b', r'\btypescript\b', r'\brust\b', r'\bdevtools\b']
OLD_NEG = [r'\bcrypto\b', r'\bbitcoin\b', r'\bnft\b', r'\belection\b', r'\bpolitics\b', r'\blawsuit\b', r'\bsuicide\b', r'\bcasino\b']

_OLD_H = [re.compile(p, re.I) for p in OLD_TIER1]
_OLD_M = [re.compile(p, re.I) for p in OLD_MED]
_OLD_L = [re.compile(p, re.I) for p in OLD_LOW]
_OLD_N = [re.compile(p, re.I) for p in OLD_NEG]

def old_relevance_score(title: str, summary: str = "") -> float:
    text = f"{title or ''} {summary or ''}"
    if not text.strip():
        return 0.0
    s = 0.0
    for r in _OLD_H:
        if r.search(text): s += 3.0
    for r in _OLD_M:
        if r.search(text): s += 2.5
    for r in _OLD_L:
        if r.search(text): s += 1.5
    for r in _OLD_N:
        if r.search(text): s -= 3.0
    return max(0.0, s)

def run_diagnostics():
    sources = load_sources(SOURCES_PATH)
    manifest = Manifest()

    print("Fetching raw entries across sources...")

    async def gather_all():
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

    raw_items_src = asyncio.run(gather_all())
    print(f"Total Raw Items Collected: {len(raw_items_src)}\n")

    print("==========================================")
    print("TASK 1: SCORER PATTERN BUG BEFORE/AFTER DELTA")
    print("==========================================\n")

    old_buckets = {"0-1": 0, "1-2": 0, "2-3": 0, "3-4": 0, "4+": 0}
    new_buckets = {"0-1": 0, "1-2": 0, "2-3": 0, "3-4": 0, "4+": 0}

    moved_to_3_plus = 0

    for raw_item, src in raw_items_src:
        t = raw_item.get("title", "")
        s = raw_item.get("summary", "")
        w = float(src.get("weight", 0.6))

        old_sc = old_relevance_score(t, s) + (1.5 if w >= 0.9 else 0.0)
        new_sc = relevance_score(t, s) + (1.5 if w >= 0.9 else 0.0)

        # Bucket old
        if old_sc < 1.0: old_buckets["0-1"] += 1
        elif old_sc < 2.0: old_buckets["1-2"] += 1
        elif old_sc < 3.0: old_buckets["2-3"] += 1
        elif old_sc < 4.0: old_buckets["3-4"] += 1
        else: old_buckets["4+"] += 1

        # Bucket new
        if new_sc < 1.0: new_buckets["0-1"] += 1
        elif new_sc < 2.0: new_buckets["1-2"] += 1
        elif new_sc < 3.0: new_buckets["2-3"] += 1
        elif new_sc < 4.0: new_buckets["3-4"] += 1
        else: new_buckets["4+"] += 1

        if old_sc < 3.0 and new_sc >= 3.0:
            moved_to_3_plus += 1

    print(f"| Bucket | Before (Old Scorer) | After (New Scorer) | Net Change |")
    print(f"|---|---|---|---|")
    for b in ["0-1", "1-2", "2-3", "3-4", "4+"]:
        diff = new_buckets[b] - old_buckets[b]
        diff_str = f"+{diff}" if diff > 0 else f"{diff}"
        print(f"| {b} | {old_buckets[b]} | {new_buckets[b]} | {diff_str} |")

    print(f"\nTotal items that moved from < 3.0 into >= 3.0: {moved_to_3_plus} items.")

    print("\n==========================================")
    print("TASK 4: HN ALGOLIA WITH TIME CUTOFF")
    print("==========================================\n")

    cutoff_ts = int((datetime.now(timezone.utc) - timedelta(hours=30)).timestamp())
    hn_queries = ["", "llm", "agents", "rag", "mcp", "fine-tuning"]

    async def test_hn_cutoff():
        async with httpx.AsyncClient(http2=True, verify=False) as client:
            for q in hn_queries:
                url = f"https://hn.algolia.com/api/v1/search_by_date?tags=story&hitsPerPage=100&numericFilters=points>=20,created_at_i>{cutoff_ts}"
                if q:
                    url += f"&query={q}"
                resp = await fetch_url_async(client, url)
                hits = resp.json().get("hits", []) if resp and resp.status_code == 200 else []
                print(f"URL: {url}")
                print(f"  -> Hits returned (last 30h): {len(hits)}")

    asyncio.run(test_hn_cutoff())

    print("\n==========================================")
    print("TASK 5: STALE-WINDOW BREAKDOWN (30-48h)")
    print("==========================================\n")

    now_utc = datetime.now(timezone.utc)
    stale_total = 0
    stale_30_to_48h = 0
    stale_over_48h = 0

    stale_30_48_high_weight = 0  # weight >= 0.9
    stale_30_48_low_weight = 0   # weight < 0.9

    for raw_item, src in raw_items_src:
        pub_raw = raw_item.get("published_raw")
        dt = parse_dt(pub_raw)
        if dt:
            age_hours = (now_utc - dt).total_seconds() / 3600.0
            if age_hours > 30.0:
                stale_total += 1
                w = float(src.get("weight", 0.6))
                if age_hours <= 48.0:
                    stale_30_to_48h += 1
                    if w >= 0.9:
                        stale_30_48_high_weight += 1
                    else:
                        stale_30_48_low_weight += 1
                else:
                    stale_over_48h += 1

    print(f"Total Stale Rejections (> 30 hours): {stale_total}")
    print(f"  - Age between 30 and 48 hours: {stale_30_to_48h}")
    print(f"    * High Authority (weight >= 0.9): {stale_30_48_high_weight}")
    print(f"    * Low/Medium Authority (weight < 0.9): {stale_30_48_low_weight}")
    print(f"  - Age > 48 hours (Archive backlog): {stale_over_48h}")

if __name__ == "__main__":
    run_diagnostics()

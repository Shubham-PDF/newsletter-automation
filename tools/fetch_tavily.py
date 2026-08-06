#!/usr/bin/env python3
"""
tools/fetch_tavily.py

WP-6: Tavily Web Search collector for live business AI implementations and friction news.
"""

import os
import sys
import json
import argparse
import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Dict
import httpx
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from tools.common import Item, parse_dt, within_window, fetch_url_async
from tools.db import Store, canonical_url, item_id

load_dotenv(override=True)

logger = logging.getLogger("fetch_tavily")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

TMP_DIR = os.path.join(BASE_DIR, ".tmp")
RAW_TAVILY_FILE = os.path.join(TMP_DIR, "raw_tavily_news.json")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "").strip()

os.makedirs(TMP_DIR, exist_ok=True)

# 15 focused vertical x intent query configurations
TAVILY_QUERIES = [
    # Business AI Implementations (verticals)
    {"query": "real estate commercial agency AI implementation automation case study", "vertical": "real_estate", "section_hint": "business"},
    {"query": "healthcare hospital patient AI deployment workflow case study", "vertical": "healthcare", "section_hint": "business"},
    {"query": "banking financial services AI automation deployment case study", "vertical": "finance", "section_hint": "business"},
    {"query": "law firm legal tech AI document automation case study", "vertical": "legal", "section_hint": "business"},
    {"query": "ecommerce retail merchant AI agent automation case study", "vertical": "ecommerce", "section_hint": "business"},

    # AI Crisis Watch & Failure Modes
    {"query": "real estate proptech AI hallucination data breach outage", "vertical": "real_estate", "section_hint": "crisis"},
    {"query": "healthcare AI medical diagnosis error privacy risk breach", "vertical": "healthcare", "section_hint": "crisis"},
    {"query": "fintech banking AI model failure compliance security vulnerability", "vertical": "finance", "section_hint": "crisis"},
    {"query": "legal tech AI hallucination fake citations court fine crisis", "vertical": "legal", "section_hint": "crisis"},
    {"query": "enterprise AI customer service bot failure crash cost overrun", "vertical": "general", "section_hint": "crisis"},

    # Launches & Developer Tools
    {"query": "new AI automation tool launch developer API SDK framework", "vertical": "devtools", "section_hint": "launches"},
    {"query": "LLM agent workflow automation tool release v0 v1", "vertical": "devtools", "section_hint": "launches"},
    {"query": "open source RAG vector database model context protocol release", "vertical": "devtools", "section_hint": "launches"},
    {"query": "AI model benchmark comparison pricing context window update", "vertical": "general", "section_hint": "headtohead"},
    {"query": "enterprise AI solution architecture case study automation", "vertical": "general", "section_hint": "business"}
]


async def fetch_tavily_query(client: httpx.AsyncClient, q_cfg: dict) -> List[Item]:
    query = q_cfg["query"]
    vertical = q_cfg["vertical"]
    section_hint = q_cfg["section_hint"]

    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "topic": "news",
        "days": 1,
        "search_depth": "advanced",
        "include_raw_content": True,
        "max_results": 4
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {TAVILY_API_KEY}"
    }

    try:
        resp = await client.post("https://api.tavily.com/search", json=payload, headers=headers, timeout=15.0)
        if resp.status_code != 200:
            logger.warning(f"Tavily query '{query}' returned status {resp.status_code}: {resp.text[:200]}")
            return []

        data = resp.json()
        results = data.get("results", [])
        items = []
        now_iso = datetime.now(timezone.utc).isoformat()

        for res in results:
            raw_url = res.get("url", "")
            if not raw_url:
                continue

            pub_raw = res.get("published_date") or res.get("published_at") or now_iso
            dt = parse_dt(pub_raw) or datetime.now(timezone.utc)

            title = res.get("title", "")
            snippet = res.get("content", "")
            raw_content = res.get("raw_content") or snippet

            c_url = canonical_url(raw_url)
            iid = item_id(raw_url)

            item = Item(
                id=iid,
                canonical=c_url,
                url=raw_url,
                title=title,
                source="Tavily Live Search",
                published_at=dt.isoformat(),
                first_seen=now_iso,
                source_type="tavily",
                score=float(res.get("score", 0.8)),
                summary=snippet[:500],
                full_text=raw_content[:4000],  # Use raw content so it skips trafilatura enrichment
                section_hint=section_hint,
                vertical=vertical,
                date_confidence="article_meta",
                raw=res
            )
            items.append(item)

        return items
    except Exception as e:
        logger.error(f"Error fetching Tavily query '{query}': {e}")
        return []


async def collect_tavily(strict: bool = False) -> List[Item]:
    if not TAVILY_API_KEY:
        msg = "CRITICAL: TAVILY_API_KEY environment variable is not configured."
        if strict:
            logger.error(msg)
            sys.exit(1)
        else:
            logger.warning(f"{msg} Continuing with empty Tavily collection.")
            with open(RAW_TAVILY_FILE, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)
            return []

    logger.info(f"Initiating 15 concurrent Tavily web searches for business AI & automation...")

    async with httpx.AsyncClient(http2=True, verify=False) as client:
        tasks = [fetch_tavily_query(client, q) for q in TAVILY_QUERIES]
        results_nested = await asyncio.gather(*tasks, return_exceptions=True)

    items: List[Item] = []
    seen_ids = set()

    for res in results_nested:
        if isinstance(res, list):
            for item in res:
                if item.id not in seen_ids:
                    seen_ids.add(item.id)
                    items.append(item)

    logger.info(f"Tavily collector retrieved {len(items)} unique items tagged with vertical and section_hint.")
    return items


def main():
    parser = argparse.ArgumentParser(description="Tavily live search collector.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero if TAVILY_API_KEY is missing.")
    args = parser.parse_args()

    items = asyncio.run(collect_tavily(strict=args.strict))

    out_dicts = [it.to_dict() for it in items]
    with open(RAW_TAVILY_FILE, "w", encoding="utf-8") as f:
        json.dump(out_dicts, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(items)} Tavily items to {RAW_TAVILY_FILE}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
tools/fetch_perplexity.py

WP-6: Perplexity collector.
Queries Perplexity API (sonar) for breaking news.
EXTRACTS CITATION URLS ONLY, DISCARDS ALL PROSE.
Extracted URLs are returned as Items to pass through standard date & dedupe filtering.
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Dict, Set
import httpx
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from tools.common import Item, parse_dt, within_window, fetch_url_async
from tools.db import Store, canonical_url, item_id

load_dotenv(override=True)

logger = logging.getLogger("fetch_perplexity")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

TMP_DIR = os.path.join(BASE_DIR, ".tmp")
RAW_PPLX_FILE = os.path.join(TMP_DIR, "raw_perplexity_urls.json")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "").strip()

os.makedirs(TMP_DIR, exist_ok=True)

TARGET_QUESTIONS = [
    "What new AI models, developer tools, APIs, or major versions were released in the last 24 hours?",
    "What real-world business AI implementations or enterprise deployments were announced today?",
    "What AI security breaches, model hallucinations, outages, or business failures occurred today?",
    "What model benchmarks, LLM pricing updates, or context window changes happened today?",
    "What real estate, legal, healthcare, or finance companies launched AI automation solutions today?",
    "What new open-source agent frameworks, RAG tools, or MCP servers were released today?",
    "What enterprise AI operational bottlenecks or cost overruns were reported in the last 24 hours?",
    "What major technical shifts or cloud infrastructure changes affecting AI developers happened today?"
]


async def query_perplexity_citations(client: httpx.AsyncClient, question: str) -> List[str]:
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "sonar",
        "messages": [
            {
                "role": "system",
                "content": "You are a technical research agent. Provide concise factual answers and citations."
            },
            {
                "role": "user",
                "content": question
            }
        ],
        "temperature": 0.1,
        "search_recency_filter": "day"
    }

    try:
        resp = await client.post("https://api.perplexity.ai/chat/completions", json=payload, headers=headers, timeout=30.0)
        if resp.status_code != 200:
            logger.warning(f"Perplexity API returned status {resp.status_code}: {resp.text[:200]}")
            return []

        data = resp.json()
        # EXTRACT CITATION URLS ONLY — DISCARD ALL PROSE
        citations = data.get("citations", [])
        if not citations:
            # Fallback check inside choices if citations placed there
            choices = data.get("choices", [])
            if choices and isinstance(choices, list):
                msg = choices[0].get("message", {})
                citations = msg.get("citations", [])

        return [c for c in citations if isinstance(c, str) and c.startswith("http")]
    except Exception as e:
        logger.error(f"Error querying Perplexity API for '{question[:40]}...': {e}")
        return []


async def collect_perplexity() -> List[Item]:
    if not PERPLEXITY_API_KEY:
        logger.warning("PERPLEXITY_API_KEY not configured. Writing empty raw_perplexity_urls.json.")
        with open(RAW_PPLX_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)
        return []

    logger.info("Initiating 8 Perplexity sonar queries to extract breaking citation URLs...")

    all_citations: Set[str] = set()
    async with httpx.AsyncClient(http2=True, verify=False) as client:
        tasks = [query_perplexity_citations(client, q) for q in TARGET_QUESTIONS]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for res in results:
            if isinstance(res, list):
                for url in res:
                    all_citations.add(url)

    logger.info(f"Perplexity collector extracted {len(all_citations)} unique raw citation URLs.")

    now_iso = datetime.now(timezone.utc).isoformat()
    items: List[Item] = []

    for url in all_citations:
        c_url = canonical_url(url)
        iid = item_id(url)

        item = Item(
            id=iid,
            canonical=c_url,
            url=url,
            title=url.split("/")[-1].replace("-", " ").replace("_", " ").title() or "Perplexity News Citation",
            source="Perplexity Live Search",
            published_at=now_iso,  # Will be re-verified from article metadata during enrichment
            first_seen=now_iso,
            source_type="perplexity",
            score=2.5,
            summary="Citation URL extracted via Perplexity sonar live search.",
            date_confidence="unverified"
        )
        items.append(item)

    return items


def main():
    items = asyncio.run(collect_perplexity())
    out_dicts = [it.to_dict() for it in items]
    with open(RAW_PPLX_FILE, "w", encoding="utf-8") as f:
        json.dump(out_dicts, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(items)} extracted Perplexity citation URLs to {RAW_PPLX_FILE}")


if __name__ == "__main__":
    main()

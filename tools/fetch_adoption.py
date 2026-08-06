#!/usr/bin/env python3
"""
tools/fetch_adoption.py

WP-D: Adoption Signal Collector.
Tracks package download metrics (PyPI, npm) and star velocity.
Emits synthetic Items ONLY when a metric moves meaningfully (WoW downloads >= 25% or stars >= 15%).
Full_text consists strictly of verified numerical metrics.
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
import httpx

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from tools.common import Item, parse_dt, within_window, fetch_url_async
from tools.db import Store, canonical_url, item_id

logger = logging.getLogger("fetch_adoption")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

TMP_DIR = os.path.join(BASE_DIR, ".tmp")
HISTORY_DIR = os.path.join(BASE_DIR, "history")
RAW_ADOPTION_FILE = os.path.join(TMP_DIR, "raw_adoption_news.json")
ADOPTION_HISTORY_FILE = os.path.join(HISTORY_DIR, "adoption.jsonl")

os.makedirs(TMP_DIR, exist_ok=True)
os.makedirs(HISTORY_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "BUILDR-AI-Newsletter-Bot/2.0 (contact@buildr.ai)"
}

PYPI_PACKAGES = [
    "langchain", "langgraph", "llama-index", "crewai", "pydantic-ai",
    "autogen-agentchat", "vllm", "ollama", "sglang", "litellm",
    "chromadb", "qdrant-client", "weaviate-client", "mcp", "dspy-ai",
    "unsloth", "n8n", "temporalio", "posthog", "apache-airflow",
    "langfuse", "deepeval"
]

NPM_PACKAGES = [
    "@langchain/core", "n8n", "@modelcontextprotocol/sdk", "chromadb", "qdrant", "posthog-js"
]

TRIGGERS = {
    "downloads_wow_pct": 25,  # 25% WoW download growth
    "stars_7d_pct": 15,        # 15% 7d star growth
}


async def fetch_pypi_downloads(client: httpx.AsyncClient, pkg: str) -> Optional[int]:
    url = f"https://pypistats.org/api/packages/{pkg}/recent"
    resp = await fetch_url_async(client, url, headers=HEADERS)
    if resp and resp.status_code == 200:
        try:
            data = resp.json().get("data", {})
            return data.get("last_week")
        except Exception:
            pass
    return None


async def fetch_npm_downloads(client: httpx.AsyncClient, pkg: str) -> Optional[int]:
    url = f"https://api.npmjs.org/downloads/point/last-week/{pkg}"
    resp = await fetch_url_async(client, url, headers=HEADERS)
    if resp and resp.status_code == 200:
        try:
            data = resp.json()
            return data.get("downloads")
        except Exception:
            pass
    return None


def load_adoption_history() -> Dict[str, Dict[str, dict]]:
    """Returns map of pkg -> {date_str -> record}"""
    history: Dict[str, Dict[str, dict]] = {}
    if os.path.exists(ADOPTION_HISTORY_FILE):
        with open(ADOPTION_HISTORY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    pkg = rec.get("pkg")
                    day = rec.get("date")
                    if pkg and day:
                        history.setdefault(pkg, {})[day] = rec
                except Exception:
                    pass
    return history


def append_adoption_history(records: List[dict]):
    with open(ADOPTION_HISTORY_FILE, "a", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")


async def collect_adoption_signals(store: Store) -> List[Item]:
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    now_iso = datetime.now(timezone.utc).isoformat()
    history = load_adoption_history()
    star_vel = store.star_velocity(days=7)

    today_records: List[dict] = []
    items: List[Item] = []

    async with httpx.AsyncClient(http2=True, verify=False) as client:
        # Fetch PyPI package stats
        pypi_tasks = [fetch_pypi_downloads(client, pkg) for pkg in PYPI_PACKAGES]
        pypi_results = await asyncio.gather(*pypi_tasks)

        for pkg, downloads in zip(PYPI_PACKAGES, pypi_results):
            if downloads is not None:
                rec = {
                    "date": today_str,
                    "pkg": pkg,
                    "ecosystem": "pypi",
                    "downloads_7d": downloads
                }
                today_records.append(rec)

        # Fetch npm package stats
        npm_tasks = [fetch_npm_downloads(client, pkg) for pkg in NPM_PACKAGES]
        npm_results = await asyncio.gather(*npm_tasks)

        for pkg, downloads in zip(NPM_PACKAGES, npm_results):
            if downloads is not None:
                rec = {
                    "date": today_str,
                    "pkg": pkg,
                    "ecosystem": "npm",
                    "downloads_7d": downloads
                }
                today_records.append(rec)

    # Append today's snapshot to history
    append_adoption_history(today_records)

    # Calculate WoW movements if 7-day prior history exists
    date_7d_ago = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")

    for rec in today_records:
        pkg = rec["pkg"]
        curr_dl = rec["downloads_7d"]
        eco = rec["ecosystem"]

        prev_rec = history.get(pkg, {}).get(date_7d_ago)
        if prev_rec:
            prev_dl = prev_rec.get("downloads_7d", 0)
            if prev_dl > 0:
                wow_pct = ((curr_dl - prev_dl) / prev_dl) * 100.0
                if wow_pct >= TRIGGERS["downloads_wow_pct"]:
                    iid = item_id(f"adoption:{pkg}:{today_str}")
                    num_text = f"{pkg} — {eco.upper()} 7d downloads: {curr_dl:,} (+{wow_pct:.1f}% WoW increase from {prev_dl:,})"
                    
                    item = Item(
                        id=iid,
                        canonical=canonical_url(f"https://pypi.org/project/{pkg}/" if eco == "pypi" else f"https://www.npmjs.com/package/{pkg}"),
                        url=f"https://pypi.org/project/{pkg}/" if eco == "pypi" else f"https://www.npmjs.com/package/{pkg}",
                        title=f"Significant Adoption Spike: {pkg} (+{wow_pct:.1f}% WoW Downloads)",
                        source="Package Adoption Tracker",
                        published_at=now_iso,
                        first_seen=now_iso,
                        source_type="pkg_stats",
                        score=5.0,
                        summary=num_text,
                        full_text=num_text,
                        section_hint="adoption_signal"
                    )
                    items.append(item)

    logger.info(f"Adoption collector processed {len(today_records)} packages and emitted {len(items)} synthetic items.")
    return items


def main():
    store = Store()
    items = asyncio.run(collect_adoption_signals(store))
    out_dicts = [it.to_dict() for it in items]

    with open(RAW_ADOPTION_FILE, "w", encoding="utf-8") as f:
        json.dump(out_dicts, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(items)} adoption signal items to {RAW_ADOPTION_FILE}")


if __name__ == "__main__":
    main()

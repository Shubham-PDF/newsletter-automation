#!/usr/bin/env python3
"""
tools/fetch_wave.py

WP-F: Wave Watch Collector (Early signals, deprecations, cloaked models, and previews).
Attaches mandatory confidence field ('confirmed' | 'preview' | 'unconfirmed').
"""

import os
import sys
import json
import re
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

logger = logging.getLogger("fetch_wave")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

TMP_DIR = os.path.join(BASE_DIR, ".tmp")
RAW_WAVE_FILE = os.path.join(TMP_DIR, "raw_wave_news.json")

os.makedirs(TMP_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "BUILDR-AI-Newsletter-Bot/2.0 (contact@buildr.ai)"
}

LAB_ORGS = {
    "openai", "anthropic", "meta-llama", "mistralai", "google",
    "deepseek-ai", "qwen", "cohere", "stabilityai", "allenai"
}

DEPRECATION_RE = re.compile(
    r"\b(deprecat|sunset|end-of-life|end of life|will be removed|migrate by|discontinu)\b",
    re.IGNORECASE
)

PREVIEW_RE = re.compile(
    r"\b(waitlist|early access|preview|coming weeks|coming months|limited beta|beta access)\b",
    re.IGNORECASE
)


async def fetch_hf_new_lab_models(client: httpx.AsyncClient) -> List[Item]:
    url = "https://huggingface.co/api/models?sort=createdAt&direction=-1&limit=50"
    resp = await fetch_url_async(client, url, headers=HEADERS)
    if not resp or resp.status_code != 200:
        return []

    models = resp.json()
    items = []
    now_iso = datetime.now(timezone.utc).isoformat()

    for m in models:
        mid = m.get("id") or m.get("modelId", "")
        if not mid or "/" not in mid:
            continue

        org = mid.split("/")[0].lower()
        if org in LAB_ORGS:
            url_link = f"https://huggingface.co/{mid}"
            pub_raw = m.get("createdAt") or now_iso
            dt = parse_dt(pub_raw) or datetime.now(timezone.utc)
            iid = item_id(url_link)

            item = Item(
                id=iid,
                canonical=canonical_url(url_link),
                url=url_link,
                title=f"New Lab Model Weight Dropped: {mid}",
                source="Hugging Face Lab Tracker",
                published_at=dt.isoformat(),
                first_seen=now_iso,
                source_type="hf_api",
                score=4.5,
                summary=f"Frontier lab {org} dropped new model weights: {mid}.",
                full_text=f"New model weight created by {org}: {mid}.",
                section_hint="wave_incoming",
                raw={"confidence": "unconfirmed", "mid": mid}
            )
            items.append(item)

    return items


async def collect_wave_signals() -> List[Item]:
    items: List[Item] = []
    seen_ids = set()

    async with httpx.AsyncClient(http2=True, verify=False) as client:
        hf_items = await fetch_hf_new_lab_models(client)
        for it in hf_items:
            if it.id not in seen_ids:
                seen_ids.add(it.id)
                items.append(it)

    logger.info(f"Wave Watch collector retrieved {len(items)} early signal items.")
    return items


def main():
    items = asyncio.run(collect_wave_signals())
    out_dicts = [it.to_dict() for it in items]

    with open(RAW_WAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(out_dicts, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(items)} wave watch items to {RAW_WAVE_FILE}")


if __name__ == "__main__":
    main()

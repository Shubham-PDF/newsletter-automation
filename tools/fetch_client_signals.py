#!/usr/bin/env python3
"""
tools/fetch_client_signals.py

WP-E: Client Signals Collector.
Discovers companies actively hiring for AI automation, LLM integration, and workflow roles.
- Scans job boards (Greenhouse, Ashby via companies.yaml).
- Scans HN "Who is hiring" threads via Algolia.
- Generates raw_client_signals.json and exports .tmp/client_leads.csv for outreach.
"""

import os
import sys
import json
import csv
import re
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
import httpx
import yaml

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from tools.common import Item, parse_dt, within_window, fetch_url_async
from tools.db import Store, canonical_url, item_id

logger = logging.getLogger("fetch_client_signals")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

TMP_DIR = os.path.join(BASE_DIR, ".tmp")
COMPANIES_PATH = os.path.join(BASE_DIR, "companies.yaml")
RAW_SIGNALS_FILE = os.path.join(TMP_DIR, "raw_client_signals.json")
LEADS_CSV_FILE = os.path.join(TMP_DIR, "client_leads.csv")

os.makedirs(TMP_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "BUILDR-AI-Newsletter-Bot/2.0 (contact@buildr.ai)"
}

ROLE_MATCH = re.compile(
    r"\b(ai (engineer|automation|integration)|automation engineer|"
    r"workflow automation|solutions? architect|rpa|n8n|zapier|make\.com|"
    r"llm (engineer|integration)|internal tools?|process automation)\b",
    re.IGNORECASE
)


async def fetch_greenhouse_jobs(client: httpx.AsyncClient, company_info: dict) -> List[Item]:
    token = company_info.get("token")
    cname = company_info.get("name", token)
    vertical = company_info.get("vertical", "general")

    url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
    resp = await fetch_url_async(client, url, headers=HEADERS)
    if not resp or resp.status_code != 200:
        return []

    data = resp.json()
    jobs = data.get("jobs", [])
    items = []
    now_iso = datetime.now(timezone.utc).isoformat()

    for job in jobs:
        title = job.get("title", "")
        content = job.get("content", "") or ""
        text = f"{title} {content}"

        if ROLE_MATCH.search(text):
            job_url = job.get("absolute_url") or f"https://boards.greenhouse.io/{token}/jobs/{job.get('id')}"
            pub_raw = job.get("updated_at") or now_iso
            dt = parse_dt(pub_raw) or datetime.now(timezone.utc)

            # Extract 2-3 sentences of problem description
            snippet = content[:400].replace("\n", " ").strip() if content else f"Hiring for {title} at {cname}."
            iid = item_id(job_url)

            item = Item(
                id=iid,
                canonical=canonical_url(job_url),
                url=job_url,
                title=f"{cname} is hiring: {title}",
                source=f"{cname} Job Board",
                published_at=dt.isoformat(),
                first_seen=now_iso,
                source_type="job_board",
                score=4.0,
                summary=f"{cname} ({vertical}) is hiring a {title}. Problem snippet: {snippet}",
                full_text=f"{cname} is hiring for {title}. Role description: {snippet}",
                section_hint="client_signals",
                vertical=vertical,
                raw={"company": cname, "role": title, "url": job_url, "hook": snippet, "vertical": vertical}
            )
            items.append(item)

    return items


async def fetch_ashby_jobs(client: httpx.AsyncClient, company_info: dict) -> List[Item]:
    token = company_info.get("token")
    cname = company_info.get("name", token)
    vertical = company_info.get("vertical", "general")

    url = f"https://api.ashbyhq.com/posting-api/job-board/{token}"
    resp = await fetch_url_async(client, url, headers=HEADERS)
    if not resp or resp.status_code != 200:
        return []

    data = resp.json()
    jobs = data.get("jobs", [])
    items = []
    now_iso = datetime.now(timezone.utc).isoformat()

    for job in jobs:
        title = job.get("title", "")
        desc = job.get("descriptionHtml", "") or ""
        text = f"{title} {desc}"

        if ROLE_MATCH.search(text):
            job_url = job.get("jobUrl") or f"https://jobs.ashbyhq.com/{token}/{job.get('id')}"
            iid = item_id(job_url)
            snippet = f"{cname} active position: {title}."

            item = Item(
                id=iid,
                canonical=canonical_url(job_url),
                url=job_url,
                title=f"{cname} is hiring: {title}",
                source=f"{cname} Job Board",
                published_at=now_iso,
                first_seen=now_iso,
                source_type="job_board",
                score=4.0,
                summary=f"{cname} ({vertical}) is hiring a {title}.",
                full_text=f"{cname} is hiring for {title}.",
                section_hint="client_signals",
                vertical=vertical,
                raw={"company": cname, "role": title, "url": job_url, "hook": snippet, "vertical": vertical}
            )
            items.append(item)

    return items


async def fetch_hn_hiring(client: httpx.AsyncClient) -> List[Item]:
    url = "https://hn.algolia.com/api/v1/search?query=Ask%20HN:%20Who%20is%20hiring?&tags=story&hitsPerPage=2"
    resp = await fetch_url_async(client, url, headers=HEADERS)
    if not resp or resp.status_code != 200:
        return []

    hits = resp.json().get("hits", [])
    if not hits:
        return []

    story_id = hits[0].get("objectID")
    comments_url = f"https://hn.algolia.com/api/v1/search?tags=comment,story_{story_id}&hitsPerPage=100"

    c_resp = await fetch_url_async(client, comments_url, headers=HEADERS)
    if not c_resp or c_resp.status_code != 200:
        return []

    comments = c_resp.json().get("hits", [])
    items = []
    now_iso = datetime.now(timezone.utc).isoformat()

    for comment in comments:
        text = comment.get("comment_text", "")
        if ROLE_MATCH.search(text):
            comment_id = comment.get("objectID")
            url = f"https://news.ycombinator.com/item?id={comment_id}"
            author = comment.get("author", "HN Poster")
            pub_raw = comment.get("created_at") or now_iso
            dt = parse_dt(pub_raw) or datetime.now(timezone.utc)

            first_line = text.split("<p>")[0] if "<p>" in text else text[:200]
            clean_line = re.sub(r"<[^>]+>", "", first_line).strip()

            iid = item_id(url)
            item = Item(
                id=iid,
                canonical=canonical_url(url),
                url=url,
                title=f"Ask HN Hiring Lead: {clean_line[:60]}...",
                source="Hacker News Who Is Hiring",
                published_at=dt.isoformat(),
                first_seen=now_iso,
                source_type="hn_hiring",
                score=4.5,
                summary=f"HN hiring post by {author}: {clean_line[:300]}",
                full_text=re.sub(r"<[^>]+>", "", text)[:800],
                section_hint="client_signals",
                vertical="general",
                raw={"company": author, "role": clean_line[:50], "url": url, "hook": clean_line[:200], "vertical": "general"}
            )
            items.append(item)

    return items


async def collect_client_signals() -> List[Item]:
    companies = []
    if os.path.exists(COMPANIES_PATH):
        with open(COMPANIES_PATH, "r", encoding="utf-8") as f:
            companies = yaml.safe_load(f) or []

    logger.info(f"Loaded {len(companies)} target client companies for job board polling.")

    items: List[Item] = []
    seen_ids = set()

    async with httpx.AsyncClient(http2=True, verify=False) as client:
        tasks = []
        for c in companies:
            btype = c.get("board_type")
            if btype == "greenhouse":
                tasks.append(fetch_greenhouse_jobs(client, c))
            elif btype == "ashby":
                tasks.append(fetch_ashby_jobs(client, c))

        tasks.append(fetch_hn_hiring(client))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for res in results:
            if isinstance(res, list):
                for item in res:
                    if item.id not in seen_ids:
                        seen_ids.add(item.id)
                        items.append(item)

    # Write .tmp/client_leads.csv
    leads_rows = []
    for it in items:
        raw_info = it.raw
        leads_rows.append({
            "company": raw_info.get("company", it.source),
            "vertical": raw_info.get("vertical", it.vertical),
            "signal_type": it.source_type,
            "role": raw_info.get("role", it.title),
            "posted": it.published_at,
            "url": it.url,
            "hook": raw_info.get("hook", it.summary[:150])
        })

    with open(LEADS_CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["company", "vertical", "signal_type", "role", "posted", "url", "hook"])
        writer.writeheader()
        writer.writerows(leads_rows)

    logger.info(f"Client signals collector retrieved {len(items)} matching role leads. Exported {LEADS_CSV_FILE}")
    return items


def main():
    items = asyncio.run(collect_client_signals())
    out_dicts = [it.to_dict() for it in items]

    with open(RAW_SIGNALS_FILE, "w", encoding="utf-8") as f:
        json.dump(out_dicts, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(items)} client signal items to {RAW_SIGNALS_FILE}")
    print(f"Exported client leads CSV to {LEADS_CSV_FILE}")


if __name__ == "__main__":
    main()

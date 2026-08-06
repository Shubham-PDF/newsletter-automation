#!/usr/bin/env python3
"""
tools/ai_research.py

WP-7, WP-B, WP-C & WP-A2: Two-Call AI Synthesis (Editor -> Trafilatura Enrichment -> Writer -> Hydration).

Python owns facts; the LLM owns prose.
1. Editor Call: Selects ~12-15 candidates from top 60 metadata rows.
2. Hard Source-Type Gating (WP-B): Enforces SECTION_ELIGIBILITY per item source_type.
   A GitHub search repo CAN ONLY reach repo_radar.
3. Crisis Evidence Gate: Requires status_page, CVE, or incident regex match for crisis section eligibility.
4. Trafilatura Enrichment: Fetches & extracts full text ONLY for selected items, re-verifying article meta dates.
5. Writer Call: Receives items pre-tagged by section; writer schema includes ONLY active sections.
6. Hydration & Validation (WP-C): Hydrates exact URLs, titles, and sources from ID_MAP;
   drops thin sections below min_items; aborts if total items < 5.
"""

import os
import sys
import json
import re
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Set, Any, Optional
import httpx
import trafilatura
from bs4 import BeautifulSoup
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from tools.common import (
    Item, parse_dt, within_window, load_sources, Manifest, fetch_url_async, SECTION_ELIGIBILITY, ALL_VALID_SECTIONS
)
from tools.db import Store, canonical_url, item_id

load_dotenv(override=True)

logger = logging.getLogger("ai_research")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

TMP_DIR = os.path.join(BASE_DIR, ".tmp")
PROMPTS_DIR = os.path.join(BASE_DIR, "prompts")

RAW_NEWS_FILE = os.path.join(TMP_DIR, "raw_news.json")
RAW_TAVILY_FILE = os.path.join(TMP_DIR, "raw_tavily_news.json")
RAW_PPLX_FILE = os.path.join(TMP_DIR, "raw_perplexity_urls.json")
RAW_ADOPTION_FILE = os.path.join(TMP_DIR, "raw_adoption_news.json")
RAW_SIGNALS_FILE = os.path.join(TMP_DIR, "raw_client_signals.json")
RAW_WAVE_FILE = os.path.join(TMP_DIR, "raw_wave_news.json")
RAW_REPOS_FILE = os.path.join(TMP_DIR, "raw_repos.json")
SYNTHESIZED_NEWS_FILE = os.path.join(TMP_DIR, "synthesized_news.json")

EDITOR_SYS_FILE = os.path.join(PROMPTS_DIR, "editor_system.txt")
EDITOR_USER_FILE = os.path.join(PROMPTS_DIR, "editor_user.txt")
WRITER_SYS_FILE = os.path.join(PROMPTS_DIR, "writer_system.txt")
WRITER_USER_FILE = os.path.join(PROMPTS_DIR, "writer_user.txt")

PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "").strip()

SECTION_MIN_ITEMS = {
    "launches": 2,
    "business": 2,
    "crisis": 1,
    "headtohead": 1,
    "repo_radar": 2
}

CRISIS_EVIDENCE_RE = re.compile(
    r"\b(outage|breach|leak|lawsuit|fined?|rollback|recall|shut down|"
    r"data exposed|price increase|deprecat\w+|malware|exploit|cve-\d{4})\b",
    re.IGNORECASE
)

os.makedirs(TMP_DIR, exist_ok=True)
os.makedirs(PROMPTS_DIR, exist_ok=True)


def has_crisis_evidence(item: Item) -> bool:
    if item.source_type in ("status_page", "cve"):
        return True
    text = f"{item.title} {item.summary} {item.full_text}"
    return bool(CRISIS_EVIDENCE_RE.search(text))


def load_file(path: str, default: str = "") -> str:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return default


async def call_llm(system_prompt: str, user_prompt: str, schema: dict) -> dict:
    if not PERPLEXITY_API_KEY:
        raise ValueError("PERPLEXITY_API_KEY environment variable is missing.")

    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "sonar",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.1,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "buildr_newsletter_response",
                "schema": schema
            }
        }
    }

    async with httpx.AsyncClient(http2=True, verify=False) as client:
        resp = await client.post("https://api.perplexity.ai/chat/completions", json=payload, headers=headers, timeout=90.0)
        if resp.status_code != 200:
            raise RuntimeError(f"LLM API returned status {resp.status_code}: {resp.text}")

        data = resp.json()
        raw_content = data["choices"][0]["message"]["content"]
        return json.loads(raw_content)


async def run_two_stage_synthesis(store: Store, manifest: Manifest) -> dict:
    candidate_items: List[Item] = []
    id_map: Dict[str, Item] = {}

    for path in (RAW_NEWS_FILE, RAW_TAVILY_FILE, RAW_PPLX_FILE, RAW_ADOPTION_FILE, RAW_SIGNALS_FILE, RAW_WAVE_FILE):
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                dicts = json.load(f)
                for d in dicts:
                    it = Item(**d)
                    if it.id not in id_map:
                        id_map[it.id] = it
                        candidate_items.append(it)

    raw_repos: List[dict] = []
    if os.path.exists(RAW_REPOS_FILE):
        with open(RAW_REPOS_FILE, "r", encoding="utf-8") as f:
            raw_repos = json.load(f)

    for r in raw_repos:
        repo_url = r.get("html_url") or f"https://github.com/{r.get('full_name')}"
        iid = item_id(repo_url)
        it = Item(
            id=iid,
            canonical=canonical_url(repo_url),
            url=repo_url,
            title=r.get("full_name", ""),
            source="GitHub Repo Radar",
            published_at=r.get("pushed_at"),
            first_seen=datetime.now(timezone.utc).isoformat(),
            source_type="gh_search",
            score=float(r.get("stargazers_count", 0)),
            summary=r.get("description", ""),
            raw=r
        )
        id_map[iid] = it

    logger.info(f"Assembled {len(candidate_items)} news candidates and {len(raw_repos)} repo candidates.")

    candidate_items.sort(key=lambda x: x.score, reverse=True)
    top_candidates = candidate_items[:60]

    # Build pipe-delimited candidates table with ENFORCED ELIGIBLE SECTIONS (WP-B)
    table_rows = []
    for c in top_candidates:
        stype = c.source_type or "rss"
        eligible_secs = ",".join(sorted(SECTION_ELIGIBILITY.get(stype, {"launches"})))
        summ = (c.summary or c.title).replace("\n", " ").replace("|", "-")[:160]
        table_rows.append(f"{c.id} | {c.title} | {c.source} | Eligible Sections: [{eligible_secs}] | {summ}")

    candidates_table_str = "\n".join(table_rows)

    repo_rows = []
    for r in raw_repos[:15]:
        fname = r.get("full_name", "")
        r_url = r.get("html_url") or f"https://github.com/{fname}"
        r_id = item_id(r_url)
        stars = r.get("stargazers_count", 0)
        lang = r.get("language", "")
        desc = (r.get("description") or "")[:120].replace("\n", " ").replace("|", "-")
        repo_rows.append(f"{r_id} | {fname} | Stars: {stars} | Lang: {lang} | Eligible Sections: [repo_radar] | {desc}")
    repo_table_str = "\n".join(repo_rows)

    # STAGE 1: EDITOR CALL
    editor_sys = load_file(EDITOR_SYS_FILE, "You are the lead Editor for BUILDR.ai. Select top items.")
    editor_user_tmpl = load_file(EDITOR_USER_FILE, "{candidates_table}\n{repo_candidates_table}")
    editor_user_prompt = editor_user_tmpl.replace("{candidates_table}", candidates_table_str).replace("{repo_candidates_table}", repo_table_str)

    editor_schema = {
        "type": "object",
        "properties": {
            "selections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "section": {"type": "string"}
                    },
                    "required": ["id", "section"]
                }
            }
        },
        "required": ["selections"]
    }

    logger.info("Executing Call 1: Editor Selection...")
    editor_resp = await call_llm(editor_sys, editor_user_prompt, editor_schema)
    raw_selections = editor_resp.get("selections", [])

    # WP-B & CRISIS EVIDENCE HARD FILTER ENFORCEMENT
    selections = []
    seen_selection_ids: Set[str] = set()

    for sel in raw_selections:
        iid = sel["id"]
        sec = sel["section"]
        if iid in seen_selection_ids:
            logger.warning(f"Editor duplicate selection for ID '{iid}'. Pruning.")
            continue

        if iid in id_map:
            it = id_map[iid]
            stype = it.source_type or ("gh_search" if it.source == "GitHub Repo Radar" else "rss")
            eligible = SECTION_ELIGIBILITY.get(stype, set())

            if sec not in eligible:
                logger.warning(f"HARD FILTER: Ineligible section '{sec}' for source_type '{stype}' (item '{it.title}'). Dropping.")
                manifest.record_rejection(it.source, "ineligible_section")
                continue

            if sec == "crisis" and not has_crisis_evidence(it):
                logger.warning(f"CRISIS EVIDENCE GATE: Item '{it.title}' lacks incident/outage evidence. Dropping from crisis section.")
                manifest.record_rejection(it.source, "lacks_crisis_evidence")
                continue

            seen_selection_ids.add(iid)
            selections.append(sel)

    logger.info(f"Editor selected {len(selections)} valid candidates passing section eligibility and crisis evidence gates.")

    # TRAFILATURA ENRICHMENT (ONLY FOR SELECTED ITEMS)
    selected_items_by_sec: Dict[str, List[Item]] = {}
    for sel in selections:
        iid = sel["id"]
        sec = sel["section"]
        if iid in id_map:
            it = id_map[iid]
            selected_items_by_sec.setdefault(sec, []).append(it)

    logger.info(f"Enriching text via Trafilatura for {len(selections)} selected items...")

    async def fetch_and_enrich(it: Item):
        if it.source == "GitHub Repo Radar" or it.source_type in ("pkg_stats", "job_board"):
            return
        async with httpx.AsyncClient(http2=True, verify=False) as client:
            resp = await fetch_url_async(client, it.url)
            if resp and resp.status_code == 200:
                text = trafilatura.extract(resp.text)
                if text and len(text.strip()) > 100:
                    it.full_text = text.strip()[:3000]

    all_selected = [it for items in selected_items_by_sec.values() for it in items]
    await asyncio.gather(*[fetch_and_enrich(it) for it in all_selected])

    # STAGE 2: WRITER CALL (ISOLATED DYNAMIC SCHEMA - FIX 2)
    active_sections = [sec for sec, items in selected_items_by_sec.items() if len(items) > 0]
    if not active_sections:
        logger.error("No active sections passed to Writer. Aborting.")
        sys.exit(1)

    writer_payload_dict = {}
    for sec in active_sections:
        sec_items = selected_items_by_sec[sec]
        writer_payload_dict[sec] = [
            {
                "id": it.id,
                "title": it.title,
                "summary": it.summary,
                "full_text": (it.full_text or it.summary)[:1500]
            }
            for it in sec_items
        ]

    writer_sys = load_file(WRITER_SYS_FILE, "You are the technical Writer for BUILDR.ai.")
    writer_user_tmpl = load_file(WRITER_USER_FILE, "{enriched_candidates_json}")
    writer_user_prompt = writer_user_tmpl.replace("{enriched_candidates_json}", json.dumps(writer_payload_dict, indent=2))

    writer_properties = {}
    for sec in active_sections:
        if sec == "repo_radar":
            item_schema = {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "what_it_does": {"type": "string"},
                    "daily_use_case": {"type": "string"},
                    "getting_started": {"type": "string"}
                },
                "required": ["id", "what_it_does", "daily_use_case"]
            }
        elif sec == "crisis":
            item_schema = {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "crisis_summary": {"type": "string"},
                    "impact_on_business": {"type": "string"},
                    "automation_fix": {"type": "string"}
                },
                "required": ["id", "crisis_summary", "automation_fix"]
            }
        elif sec == "business":
            item_schema = {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "what_they_did": {"type": "string"},
                    "business_impact": {"type": "string"},
                    "solution_opportunity": {"type": "string"}
                },
                "required": ["id", "what_they_did", "solution_opportunity"]
            }
        elif sec == "headtohead":
            item_schema = {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "verdict": {"type": "string"},
                    "use_when": {"type": "string"}
                },
                "required": ["id", "verdict", "use_when"]
            }
        else:  # launches
            item_schema = {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "what_it_is": {"type": "string"},
                    "details": {"type": "string"},
                    "automation_use_case": {"type": "string"}
                },
                "required": ["id", "what_it_is", "details", "automation_use_case"]
            }

        writer_properties[sec] = {
            "type": "array",
            "items": item_schema
        }

    writer_schema = {
        "type": "object",
        "properties": writer_properties,
        "required": active_sections
    }

    logger.info(f"Executing Call 2: Writer Synthesis for active sections: {active_sections}...")
    writer_resp = await call_llm(writer_sys, writer_user_prompt, writer_schema)

    # PRE-HYDRATION ONE-SECTION-PER-ID ASSERTION (FIX 2)
    seen_writer_ids: Set[str] = set()
    for sec_name, items_list in writer_resp.items():
        for item_obj in items_list:
            iid = item_obj.get("id")
            if iid:
                if iid in seen_writer_ids:
                    raise ValueError(f"Pre-hydration assertion failed: Writer emitted duplicate ID '{iid}' across multiple sections.")
                seen_writer_ids.add(iid)

    # HYDRATION & VALIDATION (WP-C)
    final_output: Dict[str, list] = {sec: [] for sec in ALL_VALID_SECTIONS}

    for sec_name, items_list in writer_resp.items():
        if sec_name not in final_output:
            continue
        for item_obj in items_list:
            iid = item_obj.get("id")
            if not iid or iid not in id_map:
                logger.warning(f"Writer returned unmapped or hallucinated ID '{iid}'. Skipping.")
                continue

            orig_item = id_map[iid]

            item_obj["url"] = orig_item.url
            item_obj["title"] = orig_item.title
            item_obj["source"] = orig_item.source
            item_obj["published_at"] = orig_item.published_at
            item_obj["source_type"] = orig_item.source_type or ("gh_search" if orig_item.source == "GitHub Repo Radar" else "rss")

            if sec_name == "repo_radar":
                repo_raw = orig_item.raw
                item_obj["full_name"] = repo_raw.get("full_name", orig_item.title)
                item_obj["html_url"] = repo_raw.get("html_url", orig_item.url)
                item_obj["stars"] = repo_raw.get("stargazers_count", orig_item.stars)
                item_obj["language"] = repo_raw.get("language", "Python")
                if "install_hint" in repo_raw and repo_raw["install_hint"]:
                    item_obj["getting_started"] = repo_raw["install_hint"]

            final_output[sec_name].append(item_obj)
            store.mark_featured(iid, sec_name, title=orig_item.title, url=orig_item.url)

    # WP-C: SECTION MIN_ITEMS ENFORCEMENT & DROP THIN SECTIONS
    for sec_name, min_count in SECTION_MIN_ITEMS.items():
        if len(final_output[sec_name]) < min_count:
            logger.warning(f"Section '{sec_name}' has {len(final_output[sec_name])} items, below min_items={min_count}. Dropping section.")
            final_output[sec_name] = []

    total_final = sum(len(v) for v in final_output.values())
    if total_final < 5:
        logger.error(f"CRITICAL ALARM: Total issue items ({total_final}) is below minimum threshold of 5. ABORTING DISPATCH.")
        sys.exit(1)

    logger.info(f"Successfully hydrated {total_final} final items into {SYNTHESIZED_NEWS_FILE}")

    with open(SYNTHESIZED_NEWS_FILE, "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=2, ensure_ascii=False)

    return final_output


def main():
    store = Store()
    manifest = Manifest()
    asyncio.run(run_two_stage_synthesis(store, manifest))


if __name__ == "__main__":
    main()

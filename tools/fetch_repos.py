#!/usr/bin/env python3
"""
tools/fetch_repos.py

WP-5: GitHub Repository Radar collection with star velocity ranking, quality filters,
and automated install_hint extraction from repository READMEs.
"""

import os
import sys
import json
import re
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Tuple
import httpx
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from tools.common import parse_dt, within_window, load_sources, Item, fetch_url_async
from tools.db import Store, item_id

load_dotenv(override=True)

logger = logging.getLogger("fetch_repos")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

TMP_DIR = os.path.join(BASE_DIR, ".tmp")
RAW_REPOS_FILE = os.path.join(TMP_DIR, "raw_repos.json")
SOURCES_PATH = os.path.join(BASE_DIR, "sources.yaml")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

os.makedirs(TMP_DIR, exist_ok=True)

NAME_BLOCK = re.compile(
    r'(awesome-|-awesome|interview|roadmap|course|tutorial|leetcode|cheatsheet|collection|learning-|resources|awesome_)',
    re.IGNORECASE
)

INSTALL_PATTERN = re.compile(
    r'```(?:bash|sh|shell|zsh)?\n(.*?(?:pip install|npm install|npx|uv add|docker run|brew install|go install|cargo install).*?)\n```',
    re.DOTALL | re.IGNORECASE
)

SEARCH_TOPICS = [
    "topic:ai created:>={cutoff}",
    "topic:llm created:>={cutoff}",
    "topic:agents created:>={cutoff}",
    "topic:rag created:>={cutoff}",
    "topic:mcp created:>={cutoff}"
]


def is_quality_repo(repo: dict) -> Tuple[bool, str]:
    full_name = repo.get("full_name", "")
    if NAME_BLOCK.search(full_name):
        return (False, "blocked_name_pattern")

    if not repo.get("license"):
        return (False, "null_license")

    if not repo.get("language"):
        return (False, "null_language")

    pushed_at_raw = repo.get("pushed_at")
    pdt = parse_dt(pushed_at_raw)
    ok, _ = within_window(pdt, max_hours=30 * 24)
    if not ok:
        return (False, "stale_push")

    created_raw = repo.get("created_at")
    cdt = parse_dt(created_raw)
    if cdt:
        days = max(1, (datetime.now(timezone.utc) - cdt).days)
        stars = repo.get("stargazers_count", 0)
        if (stars / days) > 500:
            return (False, "abnormal_star_velocity_ratio")

    return (True, "ok")


async def extract_install_hint(client: httpx.AsyncClient, full_name: str) -> str:
    url = f"https://api.github.com/repos/{full_name}/readme"
    headers = {"Accept": "application/vnd.github.raw+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    resp = await fetch_url_async(client, url, headers=headers)
    if resp and resp.status_code == 200:
        content = resp.text
        match = INSTALL_PATTERN.search(content)
        if match:
            lines = [l.strip() for l in match.group(1).splitlines() if l.strip() and not l.strip().startswith("#")]
            for l in lines:
                if any(kw in l for kw in ["pip install", "npm install", "npx", "uv add", "docker run", "brew install", "go install", "cargo install"]):
                    return l

    return f"git clone https://github.com/{full_name}"


async def search_github_repos(client: httpx.AsyncClient) -> List[dict]:
    cutoff_date = (datetime.now(timezone.utc) - timedelta(days=60)).strftime("%Y-%m-%d")
    all_repos: Dict[str, dict] = {}

    headers = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    else:
        logger.warning("GITHUB_TOKEN not found in env. API rate limits will be restricted.")

    for query_fmt in SEARCH_TOPICS:
        q = query_fmt.format(cutoff=cutoff_date)
        url = f"https://api.github.com/search/repositories?q={q}&sort=stars&order=desc&per_page=20"

        resp = await fetch_url_async(client, url, headers=headers)
        if resp and resp.status_code == 403:
            reset_ts = resp.headers.get("X-RateLimit-Reset")
            if reset_ts and reset_ts.isdigit():
                wait_sec = min(60, max(5, int(reset_ts) - int(datetime.now().timestamp())))
                logger.warning(f"Rate limited by GitHub API. Sleeping {wait_sec}s...")
                await asyncio.sleep(wait_sec)
                resp = await fetch_url_async(client, url, headers=headers)

        if resp and resp.status_code == 200:
            items = resp.json().get("items", [])
            for item in items:
                fn = item.get("full_name")
                if fn and fn not in all_repos:
                    all_repos[fn] = item

    return list(all_repos.values())


async def snapshot_watchlist_repos(client: httpx.AsyncClient, store: Store):
    """Snapshots the ~28 repos in sources.yaml gh_releases watchlist into store.record_stars."""
    try:
        sources = load_sources(SOURCES_PATH)
        watchlist_repos = []
        for s in sources:
            if s.get("type") == "gh_releases":
                watchlist_repos.extend(s.get("repos", []))

        headers = {"Accept": "application/vnd.github+json"}
        if GITHUB_TOKEN:
            headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

        for repo_name in set(watchlist_repos):
            url = f"https://api.github.com/repos/{repo_name}"
            resp = await fetch_url_async(client, url, headers=headers)
            if resp and resp.status_code == 200:
                data = resp.json()
                stars = data.get("stargazers_count", 0)
                store.record_stars(repo_name, stars)
    except Exception as e:
        logger.warning(f"Error snapshotting watchlist repos: {e}")


async def process_repos(store: Store) -> List[dict]:
    async with httpx.AsyncClient(http2=True, verify=False) as client:
        # Snapshot watchlist repos for star velocity history
        await snapshot_watchlist_repos(client, store)

        raw_candidates = await search_github_repos(client)
        logger.info(f"Retrieved {len(raw_candidates)} raw candidate repositories from GitHub.")

        excluded_featured = store.repos_featured_since(days=60)

        quality_candidates = []
        for repo in raw_candidates:
            fn = repo.get("full_name", "")
            if fn.lower() in excluded_featured:
                logger.info(f"Skipping repo featured in last 60d: {fn}")
                continue

            ok, reason = is_quality_repo(repo)
            if not ok:
                logger.info(f"Quality filter rejected '{fn}': {reason}")
                continue

            stars = repo.get("stargazers_count", 0)
            store.record_stars(fn, stars)
            quality_candidates.append(repo)

        # Velocity ranking vs Absolute Stars fallback
        star_vel = store.star_velocity(days=7)
        if star_vel:
            logger.info("Ranking repos using 7-day star velocity...")
            quality_candidates.sort(key=lambda r: star_vel.get(r["full_name"], r.get("stargazers_count", 0)), reverse=True)
        else:
            logger.info("Star velocity data accumulating; falling back to absolute star count ranking.")
            quality_candidates.sort(key=lambda r: r.get("stargazers_count", 0), reverse=True)

        top_candidates = quality_candidates[:15]

        # Extract install_hint for top candidates concurrently
        install_tasks = [extract_install_hint(client, r["full_name"]) for r in top_candidates]
        install_hints = await asyncio.gather(*install_tasks)

        final_repos = []
        for r, hint in zip(top_candidates, install_hints):
            r["install_hint"] = hint
            r["getting_started"] = hint
            final_repos.append(r)

        return final_repos


def main():
    store = Store()
    repos = asyncio.run(process_repos(store))
    store.save()

    with open(RAW_REPOS_FILE, "w", encoding="utf-8") as f:
        json.dump(repos, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(repos)} quality repository candidates to {RAW_REPOS_FILE}")


if __name__ == "__main__":
    main()

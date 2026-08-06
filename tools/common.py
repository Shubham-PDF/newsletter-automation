#!/usr/bin/env python3
"""
BUILDR.ai shared contract and utilities.

All collectors import this module and return list[Item].
"""

import os
import re
import random
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, List, Dict, Any
import yaml
import dateutil.parser
import httpx
from tools.db import canonical_url, item_id

logger = logging.getLogger(__name__)

VALID_SOURCE_TYPES = {
    "rss", "hn_algolia", "gh_releases", "openrouter",
    "hf_api", "reddit", "sitemap", "gh_search", "tavily", "perplexity",
    "job_board", "hn_hiring", "freelance", "pkg_stats", "benchmark",
    "vendor_blog", "status_page", "cve"
}

ALL_VALID_SECTIONS = {"launches", "business", "crisis", "headtohead", "repo_radar"}

SECTION_ELIGIBILITY = {
    "gh_search":   {"repo_radar"},                                  # HARD
    "gh_releases": {"launches"},
    "rss":         {"launches", "business", "crisis", "headtohead"},
    "hn_algolia":  {"launches", "crisis", "headtohead"},
    "status_page": {"crisis"},
    "openrouter":  {"launches", "headtohead"},
    "hf_api":      {"launches"},
    "tavily":      {"business", "crisis"},
    "perplexity":  {"business", "crisis"},
}

# Startup assertion: raise on mismatch
for stype, secs in SECTION_ELIGIBILITY.items():
    for sec in secs:
        if sec not in ALL_VALID_SECTIONS:
            raise ValueError(f"Startup assertion failed: section '{sec}' for source_type '{stype}' does not exist in pipeline section config {ALL_VALID_SECTIONS}")

@dataclass
class Item:
    id: str
    canonical: str
    url: str
    title: str
    source: str
    published_at: Optional[str]  # ISO 8601 string or None
    first_seen: str
    source_type: str = ""
    score: float = 0.0
    summary: str = ""
    full_text: str = ""
    section_hint: str = ""
    vertical: str = ""
    author: str = ""
    cluster_size: int = 1
    also_covered_by: List[str] = field(default_factory=list)
    hn_points: int = 0
    stars: int = 0
    install_hint: str = ""
    date_confidence: str = "feed"  # "feed" | "article_meta" | "unverified"
    raw: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "canonical": self.canonical,
            "url": self.url,
            "title": self.title,
            "source": self.source,
            "published_at": self.published_at,
            "first_seen": self.first_seen,
            "source_type": self.source_type,
            "score": self.score,
            "summary": self.summary,
            "full_text": self.full_text,
            "section_hint": self.section_hint,
            "vertical": self.vertical,
            "author": self.author,
            "cluster_size": self.cluster_size,
            "also_covered_by": self.also_covered_by,
            "hn_points": self.hn_points,
            "stars": self.stars,
            "install_hint": self.install_hint,
            "date_confidence": self.date_confidence,
            "raw": self.raw,
        }


def parse_dt(value: Any) -> Optional[datetime]:
    """
    Parse a datetime value (int/float timestamp, ISO 8601, RFC 2822, %Y-%m-%d, etc.)
    into a timezone-aware UTC datetime.
    Returns None on parse error. NEVER raises, NEVER guesses.
    """
    if value is None:
        return None

    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=timezone.utc)

        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)

        if isinstance(value, str):
            val_str = value.strip()
            if not val_str:
                return None

            # Numeric string check (Unix timestamp)
            if val_str.replace(".", "", 1).isdigit():
                try:
                    ts = float(val_str)
                    return datetime.fromtimestamp(ts, tz=timezone.utc)
                except Exception:
                    pass

            dt = dateutil.parser.parse(val_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            return dt
    except Exception:
        return None

    return None


def within_window(dt: Optional[datetime], max_hours: int = 30) -> Tuple[bool, str]:
    """
    Evaluates recency against max_hours (default 30h).
    Returns (True, "ok"), or (False, reason) where reason is:
    - "unparseable_date"
    - "future_dated"
    - "stale"
    """
    if dt is None:
        return (False, "unparseable_date")

    now_utc = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)

    age_seconds = (now_utc - dt).total_seconds()

    if age_seconds < -3 * 3600:
        return (False, "future_dated")

    if age_seconds > max_hours * 3600:
        return (False, "stale")

    return (True, "ok")


# Regex word boundary pattern tables compiled at module load
TIER1_MODELS_RE = re.compile(
    r"\b(chatgpt|gpt-?\d\w*|gpt|claude|gemini|llama|mistral|qwen|deepseek|"
    r"grok|copilot|cursor|codex|sora|whisper|o[1-9]\d?)\b",
    re.IGNORECASE
)

TIER2_VENDORS_RE = re.compile(
    r"\b(openai|anthropic|deepmind|hugging ?face|perplexity ai|xai|cohere)\b",
    re.IGNORECASE
)

POSITIVE_HIGH = [
    r'\bllm\b', r'\bllms\b', r'\bvllm\b', r'\bsglang\b', r'\bollama\b', r'\blitellm\b'
]

POSITIVE_MED = [
    r'\brag\b', r'\bmcp\b', r'\bagent\b', r'\bagents\b', r'\bprompting\b',
    r'\bfine-tuning\b', r'\bfinetuning\b', r'\bquantization\b', r'\bembedding\b',
    r'\bevals\b', r'\bbenchmark\b', r'\bbenchmarks\b', r'\bcontext window\b',
    r'\blangchain\b', r'\blanggraph\b', r'\bllamaindex\b', r'\bcrewai\b',
    r'\bpydantic-ai\b', r'\bautogen\b', r'\bdspy\b', r'\bunsloth\b', r'\bn8n\b',
    r'\btemporal\b', r'\blangfuse\b'
]

POSITIVE_LOW = [
    r'\bai\b', r'\bml\b', r'\blaunch\b', r'\blaunches\b', r'\brelease\b',
    r'\breleases\b', r'\bv\d+\.\d+\b', r'\bpricing\b', r'\bopen-source\b',
    r'\bweights\b', r'\binference\b', r'\bsdk\b', r'\bapi\b', r'\bapis\b',
    r'\bpython\b', r'\btypescript\b', r'\brust\b', r'\bdevtools\b'
]

NEGATIVE_PATTERNS = [
    r'\bcrypto\b', r'\bbitcoin\b', r'\bnft\b', r'\belection\b', r'\bpolitics\b',
    r'\blawsuit\b', r'\bsuicide\b', r'\bcasino\b'
]

_HIGH_RE = [re.compile(p, re.IGNORECASE) for p in POSITIVE_HIGH]
_MED_RE = [re.compile(p, re.IGNORECASE) for p in POSITIVE_MED]
_LOW_RE = [re.compile(p, re.IGNORECASE) for p in POSITIVE_LOW]
_NEG_RE = [re.compile(p, re.IGNORECASE) for p in NEGATIVE_PATTERNS]


def relevance_score(title: str, summary: str = "") -> float:
    """
    Computes a weighted relevance score based on word-boundary regex patterns.
    Threshold for inclusion is 3.0.
    """
    text = f"{title or ''} {summary or ''}"
    if not text.strip():
        return 0.0

    score = 0.0
    if TIER1_MODELS_RE.search(text):
        score += 3.0
    if TIER2_VENDORS_RE.search(text):
        score += 2.0

    for r in _HIGH_RE:
        if r.search(text):
            score += 3.0
    for r in _MED_RE:
        if r.search(text):
            score += 2.5
    for r in _LOW_RE:
        if r.search(text):
            score += 1.5
    for r in _NEG_RE:
        if r.search(text):
            score -= 3.0

    return max(0.0, score)


def load_sources(path: str) -> List[dict]:
    """
    Loads and validates sources from YAML file.
    Skips entries with enabled: false.
    Raises ValueError on unknown type or duplicate name.
    """
    if not os.path.exists(path):
        raise ValueError(f"Sources file not found at: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, list):
        raise ValueError(f"Invalid sources format in {path}: expected YAML list.")

    sources = []
    seen_names = set()

    for idx, entry in enumerate(data):
        if not isinstance(entry, dict):
            continue

        name = entry.get("name")
        if not name:
            raise ValueError(f"Source at index {idx} is missing required 'name' field.")

        if name in seen_names:
            raise ValueError(f"Duplicate source name '{name}' found in {path}.")
        seen_names.add(name)

        if entry.get("enabled") is False:
            logger.info(f"Skipping disabled source: '{name}'")
            continue

        stype = entry.get("type")
        if stype not in VALID_SOURCE_TYPES:
            raise ValueError(f"Source '{name}' has unknown type '{stype}'. Must be one of {VALID_SOURCE_TYPES}")

        sources.append(entry)

    return sources


class Manifest:
    """Accumulates counts and rejections per source for run observability."""

    def __init__(self, prompt_version: str = "v1.0"):
        self.collected: Dict[str, int] = {}
        self.rejections: Dict[str, Dict[str, int]] = {}
        self.errors: Dict[str, str] = {}
        self.prompt_version = prompt_version

    def record_collected(self, source_name: str, count: int = 1):
        self.collected[source_name] = self.collected.get(source_name, 0) + count

    def record_rejection(self, source_name: str, reason: str):
        if source_name not in self.rejections:
            self.rejections[source_name] = {}
        self.rejections[source_name][reason] = self.rejections[source_name].get(reason, 0) + 1

    def record_error(self, source_name: str, error_msg: str):
        self.errors[source_name] = error_msg

    def to_dict(self) -> dict:
        return {
            "collected": self.collected,
            "rejections": self.rejections,
            "errors": self.errors,
            "prompt_version": self.prompt_version,
        }


async def fetch_url_async(
    client: httpx.AsyncClient,
    url: str,
    headers: Optional[dict] = None,
    semaphore: Optional[asyncio.Semaphore] = None,
    max_retries: int = 3
) -> Optional[httpx.Response]:
    """
    Fetch URL with retries, exponential backoff, jitter, and optional semaphore concurrency.
    Handles 429/5xx and Retry-After headers.
    """
    req_headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 BUILDR.ai/2.0"
    }
    if headers:
        req_headers.update(headers)

    async def _do_fetch():
        for attempt in range(1, max_retries + 1):
            try:
                resp = await client.get(url, headers=req_headers, follow_redirects=True)
                if resp.status_code == 200:
                    return resp
                if resp.status_code in (429, 500, 502, 503, 504):
                    retry_after = resp.headers.get("Retry-After")
                    if retry_after and retry_after.isdigit():
                        wait_sec = float(retry_after)
                    else:
                        wait_sec = (2 ** attempt) + (random.random() * 0.5)
                    await asyncio.sleep(wait_sec)
                    continue
                return resp
            except (httpx.TransportError, httpx.TimeoutException) as e:
                if attempt == max_retries:
                    logger.warning(f"HTTP fetch failed for {url} after {max_retries} attempts: {e}")
                    return None
                wait_sec = (2 ** attempt) + (random.random() * 0.5)
                await asyncio.sleep(wait_sec)
        return None

    if semaphore:
        async with semaphore:
            return await _do_fetch()
    else:
        return await _do_fetch()

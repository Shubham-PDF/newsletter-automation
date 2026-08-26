#!/usr/bin/env python3
import os
import sys
import json
import re
import requests
import random
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load env variables (override=True ensures local .env updates take effect immediately)
load_dotenv(override=True)

# Define file paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP_DIR = os.path.join(BASE_DIR, ".tmp")
HISTORY_DIR = os.path.join(BASE_DIR, "history")
RAW_NEWS_FILE = os.path.join(TMP_DIR, "raw_news.json")
RAW_REPOS_FILE = os.path.join(TMP_DIR, "raw_repos.json")
SYNTHESIZED_NEWS_FILE = os.path.join(TMP_DIR, "synthesized_news.json")
FEATURED_REPOS_FILE = os.path.join(HISTORY_DIR, "featured_repos.json")
FEATURED_ARTICLES_FILE = os.path.join(HISTORY_DIR, "featured_articles.json")

os.makedirs(TMP_DIR, exist_ok=True)
os.makedirs(HISTORY_DIR, exist_ok=True)

# Configure Perplexity API
API_KEY = os.getenv("PERPLEXITY_API_KEY")

def load_recently_featured_articles(days=30):
    if not os.path.exists(FEATURED_ARTICLES_FILE):
        return set()
    try:
        with open(FEATURED_ARTICLES_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        seen = set()
        for entry in history:
            url = entry.get("url")
            date_str = entry.get("date")
            if url and date_str:
                try:
                    entry_date = datetime.fromisoformat(date_str)
                    if entry_date.tzinfo is None:
                        entry_date = entry_date.replace(tzinfo=timezone.utc)
                    if entry_date >= cutoff:
                        seen.add(url)
                except Exception:
                    seen.add(url)
        return seen
    except Exception as e:
        print(f"Warning: Failed to load featured articles history: {e}")
        return set()

def record_featured_history(synthesized_data):
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    # 1. Featured repos
    featured_repos = synthesized_data.get("repo_radar", [])
    if featured_repos:
        history_repos = []
        if os.path.exists(FEATURED_REPOS_FILE):
            try:
                with open(FEATURED_REPOS_FILE, "r", encoding="utf-8") as f:
                    history_repos = json.load(f)
            except Exception:
                history_repos = []
        
        existing_names = {r.get("full_name", "").lower() for r in history_repos}
        for repo in featured_repos:
            fn = repo.get("full_name")
            if fn and fn.lower() not in existing_names:
                history_repos.append({"full_name": fn, "date": today_str})
                existing_names.add(fn.lower())
                
        with open(FEATURED_REPOS_FILE, "w", encoding="utf-8") as f:
            json.dump(history_repos, f, indent=2, ensure_ascii=False)
            
    # 2. Featured article URLs
    featured_urls = []
    for sec_name in ["launches", "prompting_and_technique", "head_to_head", "tech_shifts", "business_ai", "senior_engineer"]:
        for item in synthesized_data.get(sec_name, []):
            url = item.get("url")
            if url:
                featured_urls.append(url)
                
    if featured_urls:
        history_urls = []
        if os.path.exists(FEATURED_ARTICLES_FILE):
            try:
                with open(FEATURED_ARTICLES_FILE, "r", encoding="utf-8") as f:
                    history_urls = json.load(f)
            except Exception:
                history_urls = []
                
        existing_urls = {u.get("url") for u in history_urls}
        for url in featured_urls:
            if url not in existing_urls:
                history_urls.append({"url": url, "date": today_str})
                existing_urls.add(url)
                
        with open(FEATURED_ARTICLES_FILE, "w", encoding="utf-8") as f:
            json.dump(history_urls, f, indent=2, ensure_ascii=False)

def scrape_article_text(url, default_description=""):
    """Attempts to scrape page content to provide context for the AI."""
    if not url or url.endswith(".pdf") or "arxiv.org/pdf" in url:
        return default_description
        
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=8)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "lxml")
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
            
        text = soup.get_text(separator=" ")
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        clean_text = " ".join(chunk for chunk in chunks if chunk)
        return clean_text[:6000]
    except Exception as e:
        print(f"Failed to scrape {url}: {e}. Falling back to metadata description.")
        return default_description

def calculate_candidate_score(item):
    """Deterministic candidate score based on source, HN score, and recency."""
    score = 0
    source = item.get("source", "")
    hn_score = item.get("score", 0)
    
    if source == "Hacker News":
        score += min(hn_score, 500)
    elif "TechCrunch" in source or "VentureBeat" in source:
        score += 150
    elif "OpenAI" in source or "Hugging Face" in source or "Simon Willison" in source:
        score += 200
    else:
        score += 50
        
    # Small tie-breaker
    tie_breaker = random.random()
    return score + tie_breaker

def synthesize_newsletter():
    # Strict API key check
    if not API_KEY:
        print("CRITICAL ERROR: PERPLEXITY_API_KEY environment variable is not configured or empty.")
        sys.exit(1)

    articles = []
    if os.path.exists(RAW_NEWS_FILE):
        try:
            with open(RAW_NEWS_FILE, "r", encoding="utf-8") as f:
                articles = json.load(f)
        except Exception:
            articles = []
        
    # Filter out recently featured articles
    recent_articles = load_recently_featured_articles(days=30)
    unseen_articles = [a for a in articles if a.get("url") not in recent_articles]
    if not unseen_articles and articles:
        unseen_articles = articles # Fallback if all are seen
        
    # Deterministic ranking for top 15 news candidates
    unseen_articles.sort(key=calculate_candidate_score, reverse=True)
    selected_news = unseen_articles[:15]
    
    scraped_candidates = []
    for idx, c in enumerate(selected_news):
        print(f"[{idx+1}/{len(selected_news)}] Scraping news candidate: {c['title']} ({c['source']})")
        full_text = scrape_article_text(c["url"], c.get("summary", ""))
        scraped_candidates.append({
            "title": c["title"],
            "url": c["url"],
            "source": c["source"],
            "time": c.get("published_at", ""),
            "scraped_content": full_text[:3000]
        })
        
    # Load candidate repos
    raw_repos = []
    if os.path.exists(RAW_REPOS_FILE):
        with open(RAW_REPOS_FILE, "r", encoding="utf-8") as f:
            raw_repos = json.load(f)
            
    repo_candidate_map = {r["full_name"].lower(): r for r in raw_repos}
    
    # Select top ~20 repo candidates to send to LLM
    llm_repo_candidates = raw_repos[:20]
    repo_prompt_data = [
        {
            "full_name": r["full_name"],
            "description": r["description"],
            "stars": r["stargazers_count"],
            "language": r["language"],
            "topics": r["topics"][:5],
            "html_url": r["html_url"]
        }
        for r in llm_repo_candidates
    ]

    print("Initiating Perplexity AI research & synthesis across 7 sections...")

    prompt = f"""
You are an expert technical newsletter editor compiling repobuilt for software engineers and systems builders.

═══════════════════════════════════════════════════
HARD CONSTRAINT ON NEWS RECENCY:
═══════════════════════════════════════════════════
- Select news, releases, research, and technical shifts strictly published within the last 24 hours.
- DO NOT include any story, product release, benchmark, or article that is 2 or more days old.

═══════════════════════════════════════════════════
ABSOLUTE DEDUPLICATION RULE (CRITICAL):
═══════════════════════════════════════════════════
- Each news item URL MUST appear in EXACTLY ONE section. Never reuse the same URL across multiple sections.
- Each news story/topic MUST appear in EXACTLY ONE section. If a story is relevant to multiple sections, place it ONLY in the single MOST fitting section.
- Every item across the entire newsletter must be about a DIFFERENT story, announcement, product, or event. No two items anywhere in the newsletter should cover the same thing, even with different angles.
- If you find yourself writing about the same product/model/company in two sections, STOP and keep only the one in the best-fitting section.

═══════════════════════════════════════════════════
QUALITY & ANTI-FLUFF RULES:
═══════════════════════════════════════════════════
- Each item must be genuinely informative. Major announcements (e.g., Apple announces WWDC, Google launches a new API) are absolutely valid and should be included.
- What to DROP: low-effort rehashes where multiple outlets paraphrase the same press release with zero added context — pick ONE source for that story and include the best-written version.
- Never include generic filler content that says nothing specific. Every item must have at least one concrete detail: a date, a version number, a benchmark, a pricing change, a company name, a technical decision, or a specific feature.
- "AI is transforming the industry" is fluff. "Apple announced WWDC 2026 for September 9 with new Siri SDK sessions" is a valid announcement.
- No more than 2 items from the same original source across the ENTIRE newsletter.

═══════════════════════════════════════════════════
SECTIONS (7 total — each item in exactly ONE):
═══════════════════════════════════════════════════

1. "launches" (3-5 items): New AI models, tools, products, APIs, and notable version releases from the last 24 hours. State what specific task each is for. Include major tech announcements.

2. "prompting_and_technique" (2-3 items): Practical, applicable techniques for getting better results out of models. Concrete patterns, not theory. Must include a usable example.

3. "head_to_head" (1-2 items): Comparisons between models or tools — benchmarks, pricing, context limits, real-world tradeoffs, "use X when Y". Must compare at least 2 specific named products.

4. "tech_shifts" (2-3 items): Broader infrastructure changes, deprecations, pricing moves, platform regulations, or significant outages/incidents with practical impact from the last 24 hours.

5. "repo_radar" (3-4 items): Open-source developer repositories selected ONLY from the provided candidate repo list.

6. "business_ai" (2-3 items): Real-world AI adoption and business moves. What specific companies are DEPLOYING in production, how they're using AI, funding rounds for AI startups, enterprise AI strategy shifts, and concrete ROI or impact numbers. NOT product launches (those go in section 1). Focus on: "Company X deployed Y to do Z and saw W% improvement" or "Company X raised $Y to build Z". This section should answer: "What are businesses actually doing with AI right now?"

7. "senior_engineer" (2-3 items): Production engineering wisdom and battle-tested practices. Each item MUST be a CONCRETE, ACTIONABLE lesson from real production systems. Examples of the level of specificity required:
   - "If you're using Redis for session storage, always set maxmemory-policy to allkeys-lru or you'll get OOM kills at 3 AM"
   - "When integrating Razorpay webhooks, always verify the X-Razorpay-Signature header before processing — unsigned events are a replay attack vector"
   - "PostgreSQL VACUUM can lock your table for minutes if you have 100M+ dead tuples — run pg_repack instead"
   Each item must feel like it came from someone who learned the hard way in production. Topics can include: database operations, caching strategies, payment integrations, session management, deployment pipelines, monitoring/alerting, API design pitfalls, security gotchas, scaling bottlenecks, or incident response patterns.

═══════════════════════════════════════════════════
STRICT INSTRUCTIONS FOR REPO RADAR:
═══════════════════════════════════════════════════
- You may ONLY feature repositories present in the provided Repository Candidate List below.
- Do NOT invent, guess, or modify any full_name, html_url, or star count.
- Copy full_name, html_url, stars, and language verbatim from the candidate object.
- Write a clear, 1-2 sentence "what_it_does" in plain language.
- Write a concrete "daily_use_case" (e.g., "Point it at a folder of PDFs and query them from the terminal without setting up a vector DB").
- Provide the exact single install or run command in "getting_started" (e.g. `pip install ...` or `docker run ...` or `npx ...`).

TONE AND STYLE:
- Written strictly for software developers, engineers, and technical builders.
- ZERO marketing speak, zero fluff, zero hedging (never use "in today's fast-moving landscape" or generic summaries).
- High signal, direct, precise, technical.

LIVE WEB SEARCH & NEWS CANDIDATES:
- Use both the provided News Candidates and live web search for breaking AI/technical news strictly from the last 24 hours.
- Ensure URLs are real and verified.

News Candidates:
{json.dumps(scraped_candidates, indent=2)}

Repository Candidate List (for repo_radar ONLY):
{json.dumps(repo_prompt_data, indent=2)}
"""

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    schema = {
        "type": "object",
        "properties": {
            "launches": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "url": {"type": "string"},
                        "source": {"type": "string"},
                        "what_it_is": {"type": "string"},
                        "details": {"type": "string"},
                        "why_it_matters": {"type": "string"}
                    },
                    "required": ["title", "url", "source", "what_it_is", "details", "why_it_matters"]
                }
            },
            "prompting_and_technique": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "url": {"type": "string"},
                        "source": {"type": "string"},
                        "technique": {"type": "string"},
                        "how_to_apply": {"type": "string"},
                        "example": {"type": "string"}
                    },
                    "required": ["title", "url", "source", "technique", "how_to_apply", "example"]
                }
            },
            "head_to_head": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "url": {"type": "string"},
                        "source": {"type": "string"},
                        "contenders": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "verdict": {"type": "string"},
                        "use_when": {"type": "string"}
                    },
                    "required": ["title", "url", "source", "contenders", "verdict", "use_when"]
                }
            },
            "tech_shifts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "url": {"type": "string"},
                        "source": {"type": "string"},
                        "what_it_is": {"type": "string"},
                        "details": {"type": "string"},
                        "why_it_matters": {"type": "string"}
                    },
                    "required": ["title", "url", "source", "what_it_is", "details", "why_it_matters"]
                }
            },
            "repo_radar": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "full_name": {"type": "string"},
                        "html_url": {"type": "string"},
                        "stars": {"type": "integer"},
                        "language": {"type": "string"},
                        "what_it_does": {"type": "string"},
                        "daily_use_case": {"type": "string"},
                        "getting_started": {"type": "string"}
                    },
                    "required": ["full_name", "html_url", "stars", "language", "what_it_does", "daily_use_case", "getting_started"]
                }
            },
            "business_ai": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "url": {"type": "string"},
                        "source": {"type": "string"},
                        "company": {"type": "string"},
                        "what_they_did": {"type": "string"},
                        "business_impact": {"type": "string"},
                        "takeaway_for_builders": {"type": "string"}
                    },
                    "required": ["title", "url", "source", "company", "what_they_did", "business_impact", "takeaway_for_builders"]
                }
            },
            "senior_engineer": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "url": {"type": "string"},
                        "source": {"type": "string"},
                        "topic_area": {"type": "string"},
                        "the_lesson": {"type": "string"},
                        "why_it_bites": {"type": "string"},
                        "the_fix": {"type": "string"}
                    },
                    "required": ["title", "url", "source", "topic_area", "the_lesson", "why_it_bites", "the_fix"]
                }
            }
        },
        "required": ["launches", "prompting_and_technique", "head_to_head", "tech_shifts", "repo_radar", "business_ai", "senior_engineer"]
    }

    payload = {
        "model": "sonar",
        "messages": [
            {
                "role": "system",
                "content": "You are an expert developer newsletter compiler. You produce 7 distinct sections of a technical newsletter. Respond strictly with valid JSON conforming to the requested schema. No marketing talk. CRITICAL: Never place the same story, URL, or topic in more than one section."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.2,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "newsletter_7_sections_schema",
                "schema": schema
            }
        }
    }

    try:
        response = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers=headers,
            json=payload,
            timeout=90
        )
        if response.status_code != 200:
            print(f"CRITICAL ERROR: Perplexity API returned status {response.status_code}: {response.text}")
            sys.exit(1)
            
        response_data = response.json()
        raw_content = response_data["choices"][0]["message"]["content"]
        result_json = json.loads(raw_content)
        
    except Exception as e:
        print(f"CRITICAL ERROR during Perplexity AI synthesis: {e}")
        sys.exit(1)
        
    # Post-process & validate Repo Radar entries against original fetched candidate data
    raw_repo_radar = result_json.get("repo_radar", [])
    validated_repo_radar = []
    
    for repo_item in raw_repo_radar:
        fn = repo_item.get("full_name", "").strip()
        fn_lower = fn.lower()
        
        if fn_lower in repo_candidate_map:
            candidate = repo_candidate_map[fn_lower]
            # Overwrite metadata with exact fetched values to prevent hallucinated URLs or star counts
            repo_item["full_name"] = candidate["full_name"]
            repo_item["html_url"] = candidate["html_url"]
            repo_item["stars"] = candidate["stargazers_count"]
            repo_item["language"] = candidate["language"]
            validated_repo_radar.append(repo_item)
        else:
            print(f"Warning: Dropping repo '{fn}' because it was not in the fetched raw candidate list.")
            
    result_json["repo_radar"] = validated_repo_radar

    # ═══ POST-PROCESSING DEDUPLICATION ═══
    # Even with prompt-level dedup rules, LLMs sometimes repeat the same story
    # across sections. This pass catches duplicates by URL and fuzzy title match.
    ALL_SECTIONS = ["launches", "prompting_and_technique", "head_to_head", "tech_shifts", "business_ai", "senior_engineer"]
    seen_urls = set()
    seen_titles = set()
    dedup_removed = 0

    def _normalize_title(t):
        """Normalize title for fuzzy matching: lowercase, strip punctuation, collapse whitespace."""
        t = re.sub(r'[^a-z0-9\s]', '', (t or '').lower())
        return re.sub(r'\s+', ' ', t).strip()

    for sec_name in ALL_SECTIONS:
        items = result_json.get(sec_name, [])
        deduped = []
        for item in items:
            url = (item.get("url") or "").strip().rstrip("/")
            title_norm = _normalize_title(item.get("title", ""))
            
            if url and url in seen_urls:
                print(f"  [dedup] Removed duplicate URL in '{sec_name}': {item.get('title', '')[:60]}")
                dedup_removed += 1
                continue
            if title_norm and len(title_norm) > 10 and title_norm in seen_titles:
                print(f"  [dedup] Removed duplicate title in '{sec_name}': {item.get('title', '')[:60]}")
                dedup_removed += 1
                continue
            
            if url:
                seen_urls.add(url)
            if title_norm and len(title_norm) > 10:
                seen_titles.add(title_norm)
            deduped.append(item)
        result_json[sec_name] = deduped

    if dedup_removed > 0:
        print(f"  [dedup] Removed {dedup_removed} duplicate items across sections.")

    # Also add repo URLs to seen set (repos use html_url, not url)
    for repo in result_json.get("repo_radar", []):
        repo_url = (repo.get("html_url") or "").strip().rstrip("/")
        if repo_url:
            seen_urls.add(repo_url)

    # Count total items across all 7 sections
    total_items = sum(len(result_json.get(sec, [])) for sec in ALL_SECTIONS + ["repo_radar"])
    
    if total_items == 0:
        print("CRITICAL ERROR: AI synthesis returned zero total items across all 7 sections.")
        sys.exit(1)

    # Save output to .tmp/synthesized_news.json
    with open(SYNTHESIZED_NEWS_FILE, "w", encoding="utf-8") as f:
        json.dump(result_json, f, indent=2, ensure_ascii=False)
        
    # Record history
    record_featured_history(result_json)
    
    print(f"Successfully synthesized {total_items} total items into {SYNTHESIZED_NEWS_FILE}")

if __name__ == "__main__":
    synthesize_newsletter()

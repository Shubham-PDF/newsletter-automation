#!/usr/bin/env python3
import os
import sys
import json
import requests
from datetime import datetime, timedelta, timezone

# Define file paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP_DIR = os.path.join(BASE_DIR, ".tmp")
HISTORY_DIR = os.path.join(BASE_DIR, "history")
RAW_REPOS_FILE = os.path.join(TMP_DIR, "raw_repos.json")
FEATURED_REPOS_FILE = os.path.join(HISTORY_DIR, "featured_repos.json")

os.makedirs(TMP_DIR, exist_ok=True)
os.makedirs(HISTORY_DIR, exist_ok=True)

def is_primarily_english(text):
    if not text:
        return False
    # Check ratio of ASCII printable characters
    ascii_count = sum(1 for c in text if ord(c) < 128)
    return (ascii_count / len(text)) >= 0.8

def load_recently_featured_repos(days=60):
    """Loads repos featured in the last `days` days from history/featured_repos.json."""
    if not os.path.exists(FEATURED_REPOS_FILE):
        return set()
    
    try:
        with open(FEATURED_REPOS_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
            
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        recently_featured = set()
        
        for entry in history:
            full_name = entry.get("full_name")
            date_str = entry.get("date")
            if full_name and date_str:
                try:
                    entry_date = datetime.fromisoformat(date_str)
                    if entry_date.tzinfo is None:
                        entry_date = entry_date.replace(tzinfo=timezone.utc)
                    if entry_date >= cutoff:
                        recently_featured.add(full_name.lower())
                except Exception:
                    recently_featured.add(full_name.lower())
                    
        return recently_featured
    except Exception as e:
        print(f"Warning: Failed to load featured repos history: {e}")
        return set()

def fetch_github_repos():
    github_token = os.getenv("GITHUB_TOKEN")
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "BUILDR-ai-Newsletter-Bot"
    }
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"
        print("Authenticated GitHub search API with GITHUB_TOKEN.")
    else:
        print("Unauthenticated GitHub search API (Rate limit may be restricted).")
        
    now = datetime.now(timezone.utc)
    date_90_days_ago = (now - timedelta(days=90)).strftime("%Y-%m-%d")
    date_7_days_ago = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    
    queries = [
        f"created:>{date_90_days_ago} stars:>150 topic:llm",
        f"created:>{date_90_days_ago} stars:>150 topic:ai",
        f"created:>{date_90_days_ago} stars:>150 topic:agents",
        f"created:>{date_90_days_ago} stars:>150 topic:rag",
        f"created:>{date_90_days_ago} stars:>150 topic:mcp",
        f"topic:developer-tools stars:>1000 pushed:>{date_7_days_ago}",
        f"topic:cli stars:>1000 pushed:>{date_7_days_ago}",
        f"topic:productivity stars:>1000 pushed:>{date_7_days_ago}",
        f"topic:automation stars:>1000 pushed:>{date_7_days_ago}",
        f"topic:self-hosted stars:>1000 pushed:>{date_7_days_ago}",
    ]
    
    recently_featured = load_recently_featured_repos(days=60)
    print(f"Loaded {len(recently_featured)} recently featured repos to exclude.")
    
    all_repos = {}
    
    for q in queries:
        url = f"https://api.github.com/search/repositories?q={q}&sort=stars&order=desc&per_page=10"
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                print(f"GitHub Search API query failed '{q}': Status {resp.status_code} {resp.text}")
                continue
                
            data = resp.json()
            items = data.get("items", [])
            
            for item in items:
                full_name = item.get("full_name", "")
                if not full_name:
                    continue
                    
                # Exclude archived repos
                if item.get("archived", False):
                    continue
                    
                description = item.get("description", "")
                if not description or not description.strip():
                    continue
                    
                if not is_primarily_english(description):
                    continue
                    
                if full_name.lower() in recently_featured:
                    print(f"Skipping recently featured repo: {full_name}")
                    continue
                    
                if full_name not in all_repos:
                    all_repos[full_name] = {
                        "full_name": full_name,
                        "html_url": item.get("html_url", f"https://github.com/{full_name}"),
                        "description": description.strip(),
                        "stargazers_count": item.get("stargazers_count", 0),
                        "language": item.get("language") or "N/A",
                        "topics": item.get("topics", []),
                        "pushed_at": item.get("pushed_at", ""),
                        "created_at": item.get("created_at", "")
                    }
        except Exception as e:
            print(f"Error querying GitHub API for '{q}': {e}")
            
    candidate_repos = list(all_repos.values())
    
    with open(RAW_REPOS_FILE, "w", encoding="utf-8") as f:
        json.dump(candidate_repos, f, indent=2, ensure_ascii=False)
        
    print(f"Saved {len(candidate_repos)} repository candidates to {RAW_REPOS_FILE}")
    return candidate_repos

if __name__ == "__main__":
    fetch_github_repos()

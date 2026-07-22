#!/usr/bin/env python3
import os
import sys
import json
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

# Define file paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP_DIR = os.path.join(BASE_DIR, ".tmp")
RAW_NEWS_FILE = os.path.join(TMP_DIR, "raw_news.json")

# Ensure .tmp exists
os.makedirs(TMP_DIR, exist_ok=True)

# Module-level list of RSS feeds covering AI product, tooling, and launch news
RSS_FEEDS = [
    {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/"},
    {"name": "VentureBeat AI", "url": "https://venturebeat.com/category/ai/feed/"},
    {"name": "Hugging Face Blog", "url": "https://huggingface.co/blog/feed.xml"},
    {"name": "OpenAI News", "url": "https://openai.com/news/rss.xml"},
    {"name": "MarkTechPost", "url": "https://www.marktechpost.com/feed/"},
    {"name": "Simon Willison Weblog", "url": "https://simonwillison.net/atom/entries/"},
    {"name": "InfoQ AI & ML", "url": "https://feed.infoq.com/ai-ml-data-eng/news/"}
]

# Keyword matching list focused on AI launches, techniques, benchmarks, devtools, and shifts
KEYWORDS = [
    "ai", "llm", "gpt", "claude", "gemini", "llama", "mistral", "transformer",
    "agent", "agents", "mcp", "rag", "tooling", "benchmark", "benchmarks", "evals",
    "prompting", "fine-tuning", "context window", "pricing", "launch", "release",
    "version", "open-source", "weights", "inference", "quantization", "embedding",
    "vector", "sdk", "api", "framework", "python", "typescript", "rust", "devtools"
]

def contains_keywords(text):
    if not text:
        return False
    text_lower = text.lower()
    return any(kw in text_lower for kw in KEYWORDS)

def is_within_last_24_hours(date_str_or_timestamp, max_hours=24):
    """Returns True if the item date is within the last 24 hours."""
    if not date_str_or_timestamp:
        return True
    try:
        now_utc = datetime.now(timezone.utc)
        dt = None
        
        if isinstance(date_str_or_timestamp, (int, float)):
            dt = datetime.fromtimestamp(date_str_or_timestamp, tz=timezone.utc)
        elif isinstance(date_str_or_timestamp, str):
            if date_str_or_timestamp.replace('.', '', 1).isdigit():
                dt = datetime.fromtimestamp(float(date_str_or_timestamp), tz=timezone.utc)
            elif "T" in date_str_or_timestamp:
                try:
                    dt = datetime.fromisoformat(date_str_or_timestamp.replace("Z", "+00:00"))
                except Exception:
                    pass
            if dt is None:
                try:
                    dt = parsedate_to_datetime(date_str_or_timestamp)
                except Exception:
                    pass
                    
        if dt is not None:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            age_seconds = (now_utc - dt).total_seconds()
            # Must not be older than 24 hours (86,400 seconds)
            return age_seconds <= (max_hours * 3600)
    except Exception:
        pass
    return True

def fetch_hacker_news(limit=60):
    """Fetches top, new, and show HN stories and filters them by recency (<= 24h) and keywords/score."""
    print("Fetching Hacker News (top, new, show within 24h)...")
    news_items = []
    try:
        top_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
        new_url = "https://hacker-news.firebaseio.com/v0/newstories.json"
        show_url = "https://hacker-news.firebaseio.com/v0/showstories.json"
        
        slice_size = int(limit / 3)
        top_ids = requests.get(top_url, timeout=10).json()[:slice_size]
        new_ids = requests.get(new_url, timeout=10).json()[:slice_size]
        show_ids = requests.get(show_url, timeout=10).json()[:slice_size]
        
        story_ids = list(dict.fromkeys(top_ids + show_ids + new_ids))[:limit]

        for sid in story_ids:
            try:
                story_url = f"https://hacker-news.firebaseio.com/v0/item/{sid}.json"
                story_resp = requests.get(story_url, timeout=5)
                story_resp.raise_for_status()
                story = story_resp.json()
                
                if not story or story.get("type") != "story":
                    continue
                    
                story_time = story.get("time")
                # Enforce strict 24-hour recency limit
                if not is_within_last_24_hours(story_time, max_hours=24):
                    continue
                
                title = story.get("title", "")
                url = story.get("url", "")
                text = story.get("text", "")
                score = story.get("score", 0)
                
                if contains_keywords(title) or contains_keywords(text) or score > 150:
                    news_items.append({
                        "title": title,
                        "url": url if url else f"https://news.ycombinator.com/item?id={sid}",
                        "source": "Hacker News",
                        "description": text[:300] + "..." if text else f"Hacker News story with score {score}",
                        "score": score,
                        "time": datetime.fromtimestamp(story_time, tz=timezone.utc).isoformat() if story_time else datetime.now(timezone.utc).isoformat()
                    })
            except Exception as e:
                print(f"Error fetching HN item {sid}: {e}")
    except Exception as e:
        print(f"Error fetching Hacker News stories: {e}")
    
    print(f"Fetched {len(news_items)} recent (< 24h) relevant items from Hacker News.")
    return news_items

def parse_xml_feed(content):
    """Parses XML feed content handling both standard RSS <item> and Atom <entry> elements."""
    items = []
    root = ET.fromstring(content)
    
    ns = {'atom': 'http://www.w3.org/2005/Atom'}
    atom_entries = root.findall('atom:entry', ns) or root.findall('.//{http://www.w3.org/2005/Atom}entry')
    
    if atom_entries:
        for entry in atom_entries:
            title_elem = entry.find('atom:title', ns) if entry.find('atom:title', ns) is not None else entry.find('.//{http://www.w3.org/2005/Atom}title')
            title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""
            
            link_elem = None
            for link in entry.findall('atom:link', ns) or entry.findall('.//{http://www.w3.org/2005/Atom}link'):
                if link.attrib.get('rel') in ['alternate', None]:
                    link_elem = link.attrib.get('href')
                    break
            url = link_elem if link_elem else ""
            
            summary_elem = entry.find('atom:summary', ns)
            if summary_elem is None:
                summary_elem = entry.find('atom:content', ns)
            if summary_elem is None:
                summary_elem = entry.find('.//{http://www.w3.org/2005/Atom}summary')
            desc = summary_elem.text.strip() if (summary_elem is not None and summary_elem.text) else ""
            
            updated_elem = entry.find('atom:updated', ns)
            if updated_elem is None:
                updated_elem = entry.find('atom:published', ns)
            if updated_elem is None:
                updated_elem = entry.find('.//{http://www.w3.org/2005/Atom}updated')
            pub_date = updated_elem.text.strip() if (updated_elem is not None and updated_elem.text) else datetime.now(timezone.utc).isoformat()
            
            if title and url:
                items.append((title, url, desc, pub_date))
    else:
        for item in root.findall('.//item'):
            title_elem = item.find('title')
            title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""
            
            link_elem = item.find('link')
            url = link_elem.text.strip() if link_elem is not None and link_elem.text else ""
            
            desc_elem = item.find('description')
            desc = desc_elem.text.strip() if desc_elem is not None and desc_elem.text else ""
            
            pub_elem = item.find('pubDate')
            pub_date = pub_elem.text.strip() if pub_elem is not None and pub_elem.text else datetime.now(timezone.utc).isoformat()
            
            if title and url:
                items.append((title, url, desc, pub_date))
                
    return items

def fetch_rss_feeds():
    """Fetches from RSS/Atom feeds and strictly filters items to <= 24 hours old."""
    print("Fetching RSS feeds (within 24h)...")
    news_items = []
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    for feed in RSS_FEEDS:
        try:
            response = requests.get(feed["url"], headers=headers, timeout=10)
            response.raise_for_status()
            
            entries = parse_xml_feed(response.content)
            for title, url, description, pub_date in entries:
                # Enforce strict 24-hour recency limit
                if not is_within_last_24_hours(pub_date, max_hours=24):
                    continue
                    
                if contains_keywords(title) or contains_keywords(description):
                    news_items.append({
                        "title": title,
                        "url": url,
                        "source": feed["name"],
                        "description": description[:300] + "..." if description else "",
                        "score": 0,
                        "time": pub_date
                    })
        except Exception as e:
            print(f"Error fetching RSS feed {feed['name']} ({feed['url']}): {e}")
            
    print(f"Fetched {len(news_items)} recent (< 24h) items from RSS feeds.")
    return news_items

def main():
    all_news = []
    
    # 1. Fetch from Hacker News (<= 24h)
    all_news.extend(fetch_hacker_news())
    
    # 2. Fetch RSS feeds (<= 24h)
    all_news.extend(fetch_rss_feeds())
    
    # Remove duplicates based on URL
    unique_news = []
    seen_urls = set()
    for item in all_news:
        url = item.get("url")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_news.append(item)
            
    # Write to raw_news.json
    with open(RAW_NEWS_FILE, "w", encoding="utf-8") as f:
        json.dump(unique_news, f, indent=2, ensure_ascii=False)
        
    print(f"Saved {len(unique_news)} unique raw articles (< 24h old) to {RAW_NEWS_FILE}")

if __name__ == "__main__":
    main()

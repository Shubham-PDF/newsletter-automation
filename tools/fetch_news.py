#!/usr/bin/env python3
import os
import sys
import json
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

# Define file paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP_DIR = os.path.join(BASE_DIR, ".tmp")
RAW_NEWS_FILE = os.path.join(TMP_DIR, "raw_news.json")

# Ensure .tmp exists
os.makedirs(TMP_DIR, exist_ok=True)

# Keyword matching list for generic feeds (Hacker News)
KEYWORDS = [
    "ai", "llm", "gpt", "transformer", "machine learning", "deep learning", "neural",
    "network", "routing", "tcp", "udp", "bgp", "dns", "latency", "packet", "bandwidth",
    "system design", "distributed system", "database", "microservice", "compiler",
    "cpu", "gpu", "asic", "hardware", "silicon", "architecture", "concurrency"
]

def contains_keywords(text):
    if not text:
        return False
    text_lower = text.lower()
    return any(kw in text_lower for kw in KEYWORDS)

def fetch_hacker_news(limit=50):
    """Fetches top HN stories and filters them by keywords."""
    print("Fetching Hacker News...")
    news_items = []
    try:
        # Get top and new stories IDs to make it dynamic
        top_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
        new_url = "https://hacker-news.firebaseio.com/v0/newstories.json"
        
        top_ids = requests.get(top_url, timeout=10).json()[:int(limit/2)]
        new_ids = requests.get(new_url, timeout=10).json()[:int(limit/2)]
        
        story_ids = list(set(top_ids + new_ids))[:limit]

        for sid in story_ids:
            try:
                story_url = f"https://hacker-news.firebaseio.com/v0/item/{sid}.json"
                story_resp = requests.get(story_url, timeout=5)
                story_resp.raise_for_status()
                story = story_resp.json()
                
                if not story or story.get("type") != "story":
                    continue
                
                title = story.get("title", "")
                url = story.get("url", "")
                text = story.get("text", "")
                score = story.get("score", 0)
                
                # Filter by keyword or score threshold for high signal
                if contains_keywords(title) or contains_keywords(text) or score > 150:
                    news_items.append({
                        "title": title,
                        "url": url if url else f"https://news.ycombinator.com/item?id={sid}",
                        "source": "Hacker News",
                        "description": text[:300] + "..." if text else f"Hacker News story with score {score}",
                        "time": datetime.fromtimestamp(story.get("time", datetime.now().timestamp())).isoformat()
                    })
            except Exception as e:
                print(f"Error fetching HN item {sid}: {e}")
    except Exception as e:
        print(f"Error fetching Hacker News top stories: {e}")
    
    print(f"Fetched {len(news_items)} relevant items from Hacker News.")
    return news_items

def fetch_arxiv_papers(limit=15):
    """Fetches recent preprints from arXiv under Networking, Architecture, and Language categories."""
    print("Fetching arXiv papers...")
    news_items = []
    # cs.NI: Networking, cs.AR: Hardware Architecture, cs.CL: Computation & Language (AI/NLP)
    url = f"http://export.arxiv.org/api/query?search_query=cat:cs.NI+OR+cat:cs.AR+OR+cat:cs.CL&sortBy=submittedDate&sortOrder=descending&max_results={limit}"
    
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        
        # Parse XML
        root = ET.fromstring(response.content)
        # XML Namespace mapping
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        
        for entry in root.findall('atom:entry', ns):
            try:
                title = entry.find('atom:title', ns).text.strip().replace("\n", " ")
                summary = entry.find('atom:summary', ns).text.strip().replace("\n", " ")
                published = entry.find('atom:published', ns).text.strip()
                
                # Get the link to the paper
                paper_url = ""
                for link in entry.findall('atom:link', ns):
                    if link.attrib.get('rel') == 'alternate':
                        paper_url = link.attrib.get('href', "")
                        break
                if not paper_url:
                    paper_url = entry.find('atom:id', ns).text.strip()
                
                news_items.append({
                    "title": title,
                    "url": paper_url,
                    "source": "arXiv",
                    "description": summary[:400] + "...",
                    "time": published
                })
            except Exception as e:
                print(f"Error parsing arXiv entry: {e}")
    except Exception as e:
        print(f"Error fetching arXiv papers: {e}")
        
    print(f"Fetched {len(news_items)} items from arXiv.")
    return news_items

def fetch_rss_feeds():
    """Fetches from standard technical feeds (e.g., TechCrunch)."""
    print("Fetching RSS feeds...")
    news_items = []
    feeds = [
        {"name": "TechCrunch Enterprise/AI", "url": "https://techcrunch.com/category/enterprise/feed/"}
    ]
    
    for feed in feeds:
        try:
            response = requests.get(feed["url"], timeout=10)
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            for item in root.findall('.//item'):
                try:
                    title = item.find('title').text.strip()
                    url = item.find('link').text.strip()
                    description = item.find('description').text.strip() if item.find('description') is not None else ""
                    pub_date = item.find('pubDate').text.strip() if item.find('pubDate') is not None else datetime.now().isoformat()
                    
                    if contains_keywords(title) or contains_keywords(description):
                        news_items.append({
                            "title": title,
                            "url": url,
                            "source": feed["name"],
                            "description": description[:300] + "..." if description else "",
                            "time": pub_date
                        })
                except Exception as e:
                    print(f"Error parsing RSS item from {feed['name']}: {e}")
        except Exception as e:
            print(f"Error fetching RSS feed {feed['name']}: {e}")
            
    print(f"Fetched {len(news_items)} items from RSS feeds.")
    return news_items

def main():
    all_news = []
    
    # 1. Fetch from Hacker News
    all_news.extend(fetch_hacker_news())
    
    # 2. Fetch from arXiv CS
    all_news.extend(fetch_arxiv_papers())
    
    # 3. Fetch RSS feeds
    all_news.extend(fetch_rss_feeds())
    
    # Remove duplicates based on URL
    unique_news = []
    seen_urls = set()
    for item in all_news:
        url = item.get("url")
        if url not in seen_urls:
            seen_urls.add(url)
            unique_news.append(item)
            
    # Write to raw_news.json
    with open(RAW_NEWS_FILE, "w", encoding="utf-8") as f:
        json.dump(unique_news, f, indent=2, ensure_ascii=False)
        
    print(f"Saved {len(unique_news)} unique raw articles to {RAW_NEWS_FILE}")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import os
import sys
import json
import requests
import random
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load env variables
load_dotenv()

# Define file paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP_DIR = os.path.join(BASE_DIR, ".tmp")
RAW_NEWS_FILE = os.path.join(TMP_DIR, "raw_news.json")
SYNTHESIZED_NEWS_FILE = os.path.join(TMP_DIR, "synthesized_news.json")

# Configure Perplexity API
API_KEY = os.getenv("PERPLEXITY_API_KEY")
if not API_KEY:
    print("Warning: PERPLEXITY_API_KEY environment variable is not set. AI synthesis will fail if keys are not loaded.")

def scrape_article_text(url, default_description=""):
    """Attempts to scrape page content to provide context for the AI."""
    # Skip standard pdf or non-html links
    if not url or url.endswith(".pdf") or "arxiv.org/pdf" in url:
        return default_description
        
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=8)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "lxml")
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
            
        text = soup.get_text(separator=" ")
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        clean_text = " ".join(chunk for chunk in chunks if chunk)
        
        # Truncate to avoid overloading token count
        return clean_text[:6000]
    except Exception as e:
        print(f"Failed to scrape {url}: {e}. Falling back to metadata description.")
        return default_description

def synthesize_newsletter():
    if not os.path.exists(RAW_NEWS_FILE):
        print(f"Error: {RAW_NEWS_FILE} not found. Run fetch_news.py first.")
        sys.exit(1)
        
    with open(RAW_NEWS_FILE, "r", encoding="utf-8") as f:
        articles = json.load(f)
        
    if not articles:
        print("No articles fetched. Exiting.")
        return
        
    print(f"Loaded {len(articles)} articles. Selecting and scraping top candidates...")
    
    # Sort and split candidates to ensure variety across runs
    arxiv_items = [x for x in articles if x.get("source") == "arXiv"]
    other_items = [x for x in articles if x.get("source") != "arXiv"]
    
    # Grab top 5 arXiv papers (sorted by date)
    selected_arxiv = sorted(arxiv_items, key=lambda x: x.get("time", ""), reverse=True)[:5]
    
    # Shuffle and pick 10 items from Hacker News and RSS feeds for dynamic variation
    random.shuffle(other_items)
    selected_others = other_items[:10]
    
    candidates = selected_arxiv + selected_others
    random.shuffle(candidates) # Mix them up
    
    scraped_candidates = []
    for idx, c in enumerate(candidates):
        print(f"[{idx+1}/{len(candidates)}] Scraping: {c['title']} ({c['source']})")
        full_text = scrape_article_text(c["url"], c["description"])
        scraped_candidates.append({
            "title": c["title"],
            "url": c["url"],
            "source": c["source"],
            "time": c["time"],
            "scraped_content": full_text[:4000] # Pass first 4k chars to LLM
        })
        
    print("Initiating Perplexity AI research & synthesis...")
    
    prompt = f"""
You are an expert technical newsletter editor. Review the provided {len(scraped_candidates)} candidate articles/papers.
Also, perform a real-time web search to find any other major breaking technical news or research papers from the last 24 hours regarding:
1. Artificial Intelligence / LLMs / Deep Learning
2. Computer Networks & Internet Infrastructure
3. Computer Systems Design & Hardware Architecture

Select the top 6 most high-signal, impactful stories from the provided candidates AND your live web search.
Ensure that at least 2 stories are from your live web search to bring in fresh, real-time news not present in the static candidate list.

For each selected story, write a detailed, developer-centric newsletter section.
- For stories selected from the candidate list, copy the exact URL provided.
- For stories found via live web search, provide their real, verified source URL.
- For the "what_it_is", "technical_deep_dive", and "why_it_matters" fields, write technical, content-rich overviews (never generic placeholders).

Here is the candidate news data:
{json.dumps(scraped_candidates, indent=2)}
"""

    if not API_KEY:
        print("Error: PERPLEXITY_API_KEY is not configured. Creating fallback empty structure.")
        fallback = {"articles": []}
        with open(SYNTHESIZED_NEWS_FILE, "w", encoding="utf-8") as f:
            json.dump(fallback, f, indent=2)
        return

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    schema = {
        "type": "object",
        "properties": {
            "articles": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": { "type": "string" },
                        "url": { "type": "string" },
                        "source": { "type": "string" },
                        "category": { 
                           "type": "string", 
                           "enum": ["Artificial Intelligence", "Computer Networks", "Computer Systems Design"] 
                        },
                        "relevance_score": { "type": "integer" },
                        "what_it_is": { "type": "string", "description": "Concise 1-2 sentence summary of what this news/paper is about." },
                        "technical_deep_dive": { "type": "string", "description": "Detailed developer-centric breakdown explaining how it works under the hood (e.g. architecture, algorithm, protocol, data structures)." },
                        "why_it_matters": { "type": "string", "description": "Operational, architectural, or industry impact (e.g. 'reduces latency by X%', 'allows X at scale')." }
                    },
                    "required": ["title", "url", "source", "category", "relevance_score", "what_it_is", "technical_deep_dive", "why_it_matters"]
                }
            }
        },
        "required": ["articles"]
    }

    payload = {
        "model": "sonar",
        "messages": [
            {
                "role": "system",
                "content": "You are an expert technical newsletter writer with 10+ years of experience in computer science. Respond strictly with JSON conforming to the requested schema."
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
                "name": "newsletter_schema",
                "schema": schema
            }
        }
    }

    try:
        response = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        
        response_data = response.json()
        raw_text_response = response_data["choices"][0]["message"]["content"]
        
        # Save output to .tmp/synthesized_news.json
        result_json = json.loads(raw_text_response)
        
        with open(SYNTHESIZED_NEWS_FILE, "w", encoding="utf-8") as f:
            json.dump(result_json, f, indent=2, ensure_ascii=False)
            
        print(f"Successfully synthesized {len(result_json.get('articles', []))} articles into {SYNTHESIZED_NEWS_FILE}")
        
    except Exception as e:
        print(f"Error during Perplexity AI synthesis: {e}")
        if 'response' in locals() and response is not None:
            print(f"Response status: {response.status_code}. Response text: {response.text}")
        fallback = {"articles": []}
        with open(SYNTHESIZED_NEWS_FILE, "w", encoding="utf-8") as f:
            json.dump(fallback, f, indent=2)

if __name__ == "__main__":
    synthesize_newsletter()

#!/usr/bin/env python3
import pytest
from datetime import datetime, timezone, timedelta
from tools.common import Item, parse_dt, within_window, Manifest
from tools.db import Store, item_id
from tools.fetch_news import fetch_and_filter_news

def test_was_featured_rejected():
    store = Store()
    featured_url = "https://example.com/already-featured-story"
    iid = item_id(featured_url)
    
    # Mark as featured today
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    store.mark_featured(iid, "launches", title="Already Featured", url=featured_url, issue_date=today_str)
    
    assert store.was_featured(featured_url, days=30) is True

def test_surviving_items_validity():
    store = Store()
    manifest = Manifest()
    
    # Run fetch_and_filter_news
    import asyncio
    items = asyncio.run(fetch_and_filter_news(store, manifest))
    
    for item in items:
        assert item.id != ""
        assert item.published_at is not None
        ok, reason = within_window(parse_dt(item.published_at), max_hours=30)
        assert ok is True

if __name__ == "__main__":
    test_was_featured_rejected()
    test_surviving_items_validity()
    print("All WP-3 fetch_news.py tests PASSED successfully!")

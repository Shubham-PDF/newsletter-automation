#!/usr/bin/env python3
import pytest
from datetime import datetime, timezone, timedelta
from tools.common import Item, parse_dt, within_window, relevance_score, load_sources, Manifest
from tools.db import canonical_url, item_id

def test_malformed_date_rejected():
    dt = parse_dt("not-a-valid-date-string")
    assert dt is None
    ok, reason = within_window(dt)
    assert ok is False
    assert reason == "unparseable_date"

def test_future_date_rejected():
    future_dt = datetime.now(timezone.utc) + timedelta(hours=10)
    ok, reason = within_window(future_dt)
    assert ok is False
    assert reason == "future_dated"

def test_canonical_url_collapse():
    url1 = "https://www.techcrunch.com/article/vllm-release/?utm_source=rss&utm_medium=feed"
    url2 = "https://m.techcrunch.com/article/vllm-release/amp"
    url3 = "https://techcrunch.com/article/vllm-release"

    c1 = canonical_url(url1)
    c2 = canonical_url(url2)
    c3 = canonical_url(url3)

    assert c1 == c3
    assert c2 == c3
    assert item_id(url1) == item_id(url2) == item_id(url3)

def test_relevance_score_word_boundaries():
    # "maintainer" contains "ai", but word boundary \bai\b prevents false positive match
    noise_score = relevance_score("Maintainer update for generic repository")
    assert noise_score < 3.0

    # "vLLM v0.7 ships FP8 inference" matches vllm (+3.0), v0.7 (+1.5), inference (+1.5)
    real_news_score = relevance_score("vLLM v0.7 ships FP8 inference")
    assert real_news_score >= 3.0

if __name__ == "__main__":
    test_malformed_date_rejected()
    test_future_date_rejected()
    test_canonical_url_collapse()
    test_relevance_score_word_boundaries()
    print("All WP-1 common.py tests PASSED successfully!")

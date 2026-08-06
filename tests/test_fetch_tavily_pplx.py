#!/usr/bin/env python3
import pytest
from tools.common import Item
from tools.fetch_tavily import TAVILY_QUERIES, collect_tavily
from tools.fetch_perplexity import TARGET_QUESTIONS, collect_perplexity

def test_tavily_queries_configuration():
    assert len(TAVILY_QUERIES) == 15
    for q in TAVILY_QUERIES:
        assert "query" in q
        assert "vertical" in q
        assert "section_hint" in q
        assert q["vertical"] in ["real_estate", "healthcare", "finance", "legal", "ecommerce", "manufacturing", "supply_chain", "devtools", "general"]

def test_perplexity_questions_configuration():
    assert len(TARGET_QUESTIONS) == 8
    for q in TARGET_QUESTIONS:
        assert isinstance(q, str) and len(q) > 20

if __name__ == "__main__":
    test_tavily_queries_configuration()
    test_perplexity_questions_configuration()
    print("All WP-6 Tavily and Perplexity tests PASSED successfully!")

#!/usr/bin/env python3
import pytest
from tools.common import Item, SECTION_ELIGIBILITY, ALL_VALID_SECTIONS
from tools.ai_research import has_crisis_evidence
from tools.quality_gates import run_all_quality_gates

def test_startup_assertion_and_section_keys():
    # Verify all section keys in SECTION_ELIGIBILITY exist in ALL_VALID_SECTIONS
    for stype, secs in SECTION_ELIGIBILITY.items():
        for sec in secs:
            assert sec in ALL_VALID_SECTIONS, f"Invalid section {sec} in SECTION_ELIGIBILITY"

def test_crisis_evidence_gate():
    # Item with crisis evidence (e.g. outage)
    outage_item = Item(
        id="1", canonical="https://a.com/1", url="https://a.com/1",
        title="OpenAI API Outage Causes Incident", source="OpenAI Status",
        published_at="2026-08-06T00:00:00Z", first_seen="2026-08-06T00:00:00Z",
        source_type="status_page"
    )
    assert has_crisis_evidence(outage_item) is True

    # Item without crisis evidence (e.g. general launch)
    launch_item = Item(
        id="2", canonical="https://a.com/2", url="https://a.com/2",
        title="Amazon Aurora serverless now scales faster", source="AWS What's New",
        published_at="2026-08-06T00:00:00Z", first_seen="2026-08-06T00:00:00Z",
        source_type="rss", summary="Scales faster to support agentic AI"
    )
    assert has_crisis_evidence(launch_item) is False

def test_quality_gates_passed():
    diverse_payload = {
        "launches": [
            {"id": "1", "title": "Model 1", "source_type": "rss", "url": "https://a.com/1", "what_it_is": "A", "details": "B", "automation_use_case": "D"},
            {"id": "2", "title": "Model 2", "source_type": "openrouter", "url": "https://a.com/2", "what_it_is": "A", "details": "B", "automation_use_case": "D"}
        ],
        "business": [
            {"id": "3", "title": "Hiring 1", "source_type": "tavily", "url": "https://a.com/3", "what_they_did": "Need AI engineer", "solution_opportunity": "Build RAG pipeline"},
            {"id": "4", "title": "Hiring 2", "source_type": "perplexity", "url": "https://a.com/4", "what_they_did": "Need n8n workflow", "solution_opportunity": "Automate CRM sync"}
        ],
        "repo_radar": [
            {"id": "5", "title": "Repo 1", "source_type": "gh_search", "url": "https://a.com/5", "what_it_does": "Tool", "daily_use_case": "Use case", "getting_started": "pip install tool"}
        ],
        "crisis": [],
        "headtohead": []
    }

    passed, errors = run_all_quality_gates(diverse_payload)
    assert passed is True
    assert len(errors) == 0

if __name__ == "__main__":
    test_startup_assertion_and_section_keys()
    test_crisis_evidence_gate()
    test_quality_gates_passed()
    print("All WP v2 remediation tests PASSED successfully!")

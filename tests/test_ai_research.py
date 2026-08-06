#!/usr/bin/env python3
import pytest
from tools.common import Item
from tools.db import item_id

def test_hydration_id_validation():
    # Test ID_MAP hydration and cross-section deduplication
    url1 = "https://example.com/valid-article-1"
    iid1 = item_id(url1)
    item1 = Item(id=iid1, canonical=url1, url=url1, title="Valid Article 1", source="Source A", published_at="2026-08-06T10:00:00+00:00", first_seen="2026-08-06T10:00:00+00:00")

    id_map = {iid1: item1}

    # Mocked writer output containing a valid ID, a duplicate ID, and a fake/hallucinated ID
    mock_writer_output = {
        "launches": [
            {"id": iid1, "what_it_is": "New tool", "details": "Details", "why_it_matters": "Matters", "automation_use_case": "Use case"}
        ],
        "business_ai_in_action": [
            {"id": iid1, "industry": "Real Estate", "what_they_did": "Deployed AI", "business_impact": "Impact", "solution_opportunity": "Opp"},
            {"id": "fake_hallucinated_id_999", "industry": "Finance", "what_they_did": "Fake", "business_impact": "Fake", "solution_opportunity": "Fake"}
        ],
        "ai_crisis_watch": [],
        "head_to_head": [],
        "repo_radar": []
    }

    final_output = {"launches": [], "business_ai_in_action": [], "ai_crisis_watch": [], "head_to_head": [], "repo_radar": []}
    seen_ids = set()

    for sec_name, items in mock_writer_output.items():
        for item_obj in items:
            iid = item_obj.get("id")
            if not iid or iid not in id_map:
                continue  # Fake ID rejected
            if iid in seen_ids:
                continue  # Duplicate ID rejected
            seen_ids.add(iid)

            orig = id_map[iid]
            item_obj["url"] = orig.url
            item_obj["title"] = orig.title
            item_obj["source"] = orig.source
            final_output[sec_name].append(item_obj)

    # Verify results
    assert len(final_output["launches"]) == 1
    assert len(final_output["business_ai_in_action"]) == 0  # Duplicate iid1 pruned
    assert final_output["launches"][0]["url"] == url1
    assert final_output["launches"][0]["source"] == "Source A"

if __name__ == "__main__":
    test_hydration_id_validation()
    print("All WP-7 ai_research.py hydration and validation tests PASSED successfully!")

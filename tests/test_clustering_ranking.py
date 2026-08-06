#!/usr/bin/env python3
import pytest
from datetime import datetime, timezone
from tools.common import Item
from tools.fetch_news import cluster_items, rank_items

def test_jaccard_clustering():
    sources_map = {
        "TechCrunch AI": {"weight": 0.6},
        "OpenAI News": {"weight": 1.0},
        "Hacker News": {"weight": 0.7},
        "VentureBeat AI": {"weight": 0.6}
    }
    
    now_iso = datetime.now(timezone.utc).isoformat()
    
    # 4 near-duplicate headlines for the same story
    item1 = Item(id="1", canonical="c1", url="https://tc.com/vllm", title="vLLM Releases v0.7 with FP8 Inference Support", source="TechCrunch AI", published_at=now_iso, first_seen=now_iso)
    item2 = Item(id="2", canonical="c2", url="https://openai.com/vllm", title="vLLM v0.7 Released with FP8 Inference", source="OpenAI News", published_at=now_iso, first_seen=now_iso)
    item3 = Item(id="3", canonical="c3", url="https://hn.com/item/100", title="vLLM 0.7 Ships FP8 Inference Support", source="Hacker News", published_at=now_iso, first_seen=now_iso)
    item4 = Item(id="4", canonical="c4", url="https://vb.com/vllm", title="vLLM Releases v0.7 for FP8 Inference", source="VentureBeat AI", published_at=now_iso, first_seen=now_iso)

    items = [item1, item2, item3, item4]
    
    clustered = cluster_items(items, sources_map, threshold=0.55)
    
    assert len(clustered) == 1
    rep = clustered[0]
    assert rep.cluster_size == 4
    assert len(rep.also_covered_by) == 3
    # OpenAI News has weight 1.0, so item2 should be chosen as representative
    assert rep.source == "OpenAI News"

def test_composite_ranking():
    sources_map = {"SourceA": {"weight": 1.0}, "SourceB": {"weight": 0.5}}
    now_iso = datetime.now(timezone.utc).isoformat()
    
    item1 = Item(id="1", canonical="c1", url="https://a.com/1", title="Low score item", source="SourceB", published_at=now_iso, first_seen=now_iso, score=3.0, cluster_size=1)
    item2 = Item(id="2", canonical="c2", url="https://a.com/2", title="High score item", source="SourceA", published_at=now_iso, first_seen=now_iso, score=8.0, cluster_size=3)

    ranked = rank_items([item1, item2], sources_map)
    assert ranked[0].id == "2"
    assert ranked[0].score > ranked[1].score

if __name__ == "__main__":
    test_jaccard_clustering()
    test_composite_ranking()
    print("All WP-4 clustering and ranking tests PASSED successfully!")

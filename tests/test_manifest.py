#!/usr/bin/env python3
import pytest
from tools.common import Manifest
from tools.db import Store

def test_manifest_recording():
    store = Store()
    manifest = Manifest(prompt_version="v2.0-editor-writer")

    manifest.record_collected("OpenAI News", 3)
    manifest.record_rejection("OpenAI News", "stale")
    manifest.record_rejection("TechCrunch AI", "low_score")

    data = manifest.to_dict()
    assert data["collected"]["OpenAI News"] == 3
    assert data["rejections"]["OpenAI News"]["stale"] == 1
    assert data["prompt_version"] == "v2.0-editor-writer"

    store.record_run(data, run_id="test_run_123")
    counts = store.save()
    assert counts["runs"] >= 1

if __name__ == "__main__":
    test_manifest_recording()
    print("All WP-9 manifest tests PASSED successfully!")

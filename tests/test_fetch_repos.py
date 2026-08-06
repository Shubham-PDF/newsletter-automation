#!/usr/bin/env python3
import pytest
from datetime import datetime, timezone, timedelta
from tools.fetch_repos import is_quality_repo

def test_awesome_list_rejected():
    awesome_repo = {
        "full_name": "developer/awesome-ai-agents",
        "license": {"key": "mit"},
        "language": "Python",
        "pushed_at": datetime.now(timezone.utc).isoformat(),
        "created_at": (datetime.now(timezone.utc) - timedelta(days=10)).isoformat(),
        "stargazers_count": 100
    }
    ok, reason = is_quality_repo(awesome_repo)
    assert ok is False
    assert reason == "blocked_name_pattern"

def test_null_license_or_language_rejected():
    no_license = {
        "full_name": "developer/real-tool",
        "license": None,
        "language": "Python",
        "pushed_at": datetime.now(timezone.utc).isoformat(),
        "created_at": (datetime.now(timezone.utc) - timedelta(days=10)).isoformat(),
        "stargazers_count": 100
    }
    ok, reason = is_quality_repo(no_license)
    assert ok is False
    assert reason == "null_license"

def test_valid_repo_passes():
    valid_repo = {
        "full_name": "vllm-project/vllm",
        "license": {"key": "apache-2.0"},
        "language": "Python",
        "pushed_at": datetime.now(timezone.utc).isoformat(),
        "created_at": (datetime.now(timezone.utc) - timedelta(days=200)).isoformat(),
        "stargazers_count": 15000
    }
    ok, reason = is_quality_repo(valid_repo)
    assert ok is True

if __name__ == "__main__":
    test_awesome_list_rejected()
    test_null_license_or_language_rejected()
    test_valid_repo_passes()
    print("All WP-5 fetch_repos.py tests PASSED successfully!")

#!/usr/bin/env python3
"""
run_newsletter.py

BUILDR.ai Daily Newsletter Orchestrator.
Executes all collectors, two-stage AI synthesis, pre-send quality gates, HTML compilation, and email dispatch.
"""

import os
import sys
import time
import json
import argparse
import subprocess
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from tools.db import Store
from tools.quality_gates import run_all_quality_gates

TMP_DIR = os.path.join(BASE_DIR, ".tmp")
SYNTHESIZED_NEWS_FILE = os.path.join(TMP_DIR, "synthesized_news.json")


def run_script(script_path):
    print(f"\n==========================================")
    print(f"Running: {os.path.basename(script_path)}")
    print(f"==========================================\n")

    result = subprocess.run([sys.executable, script_path], capture_output=False)
    if result.returncode != 0:
        print(f"Error: {script_path} failed with return code {result.returncode}")
        sys.exit(result.returncode)


def main():
    parser = argparse.ArgumentParser(description="Run the BUILDR.ai Newsletter Pipeline.")
    parser.add_argument("--dry-run", action="store_true", help="Fetch news/repos and generate HTML, but do not send email.")
    args = parser.parse_args()

    start_time = time.time()
    tools_dir = os.path.join(BASE_DIR, "tools")
    preview_html_path = os.path.join(BASE_DIR, ".tmp", "newsletter.html")

    # 1. News Collectors (Stages 1-5)
    run_script(os.path.join(tools_dir, "fetch_news.py"))

    # 2. Live Search Collectors (Tavily & Perplexity)
    run_script(os.path.join(tools_dir, "fetch_tavily.py"))
    run_script(os.path.join(tools_dir, "fetch_perplexity.py"))

    # 3. GitHub Repo Radar
    run_script(os.path.join(tools_dir, "fetch_repos.py"))

    # 4. Adoption Signal Collector
    run_script(os.path.join(tools_dir, "fetch_adoption.py"))

    # 5. Client Signals & Job Leads Collector
    run_script(os.path.join(tools_dir, "fetch_client_signals.py"))

    # 6. Wave Watch Collector
    run_script(os.path.join(tools_dir, "fetch_wave.py"))

    # 7. Two-Stage AI Synthesis
    run_script(os.path.join(tools_dir, "ai_research.py"))

    # 8. WP-H Pre-Send Quality Gates Check
    print("\n==========================================")
    print("Running WP-H Pre-Send Quality Gates Check")
    print("==========================================\n")

    if not os.path.exists(SYNTHESIZED_NEWS_FILE):
        print(f"Error: {SYNTHESIZED_NEWS_FILE} missing.")
        sys.exit(1)

    with open(SYNTHESIZED_NEWS_FILE, "r", encoding="utf-8") as f:
        payload = json.load(f)

    passed, gate_errors = run_all_quality_gates(payload)
    if not passed:
        print("\nCRITICAL QUALITY GATE FAILURE! ABORTING DISPATCH.")
        for err in gate_errors:
            print(f"  - {err}")
        sys.exit(1)

    print("ALL 6 PRE-SEND QUALITY GATES PASSED SUCCESSFULLY!")

    # 9. Generate HTML
    run_script(os.path.join(tools_dir, "generate_html.py"))

    # Record run manifest into Store
    duration_sec = round(time.time() - start_time, 2)
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    store = Store()
    health_7d = store.source_health(days=7)
    manifest_data = {
        "run_id": f"run_{today_str}_{int(time.time())}",
        "date": today_str,
        "duration_seconds": duration_sec,
        "dry_run": args.dry_run,
        "source_health_7d": health_7d,
        "status": "success"
    }
    store.record_run(manifest_data, run_id=manifest_data["run_id"])
    store.save()

    # 10. Dispatch Email (Skipped during dry-run)
    if args.dry_run:
        print(f"\n[Dry-Run Mode] Email dispatch skipped. Duration: {duration_sec}s.")
        print(f"[Dry-Run Preview] Preview HTML generated at: {preview_html_path}")
    else:
        run_script(os.path.join(tools_dir, "send_email.py"))
        print(f"\n[Success] Newsletter generated and dispatched in {duration_sec}s!")


if __name__ == "__main__":
    main()

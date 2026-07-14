#!/usr/bin/env python3
import os
import sys
import argparse
import subprocess

def run_script(script_path):
    print(f"\n==========================================")
    print(f"Running: {os.path.basename(script_path)}")
    print(f"==========================================\n")
    
    result = subprocess.run([sys.executable, script_path], capture_output=False)
    if result.returncode != 0:
        print(f"Error: {script_path} failed with return code {result.returncode}")
        sys.exit(result.returncode)

def main():
    parser = argparse.ArgumentParser(description="Run the AI & Systems Newsletter Pipeline.")
    parser.add_argument("--dry-run", action="store_true", help="Fetch news and generate HTML, but do not send email.")
    args = parser.parse_args()
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    tools_dir = os.path.join(base_dir, "tools")
    
    # 1. Fetch news
    run_script(os.path.join(tools_dir, "fetch_news.py"))
    
    # 2. Synthesize using AI
    run_script(os.path.join(tools_dir, "ai_research.py"))
    
    # 3. Generate HTML
    run_script(os.path.join(tools_dir, "generate_html.py"))
    
    # 4. Dispatch Email
    if args.dry_run:
        print("\n[Dry-Run Override] Executing email dispatch during dry-run...")
    run_script(os.path.join(tools_dir, "send_email.py"))
    print("\n[Success] Newsletter generated and dispatched!")

if __name__ == "__main__":
    main()

# Workflow: Daily BUILDR.ai Technical Briefing

This Standard Operating Procedure (SOP) outlines the execution protocol for generating and dispatching the daily technical newsletter.

## Objective
To deliver a high-signal, developer and AI consultant newsletter structured into 5 core sections:
1. Launches & AI Tools (with Automation Engineer Use Cases)
2. Business AI in Action & Industry Solutions (Real Estate, Healthcare, Legal, Finance case studies)
3. AI Friction & Crisis Watch (Solvable bottlenecks, operational failures, and automation fixes)
4. Head to Head & Task Matrix (Task-based model selection guidance)
5. Automation Repo Radar (Featured Open-Source GitHub Repositories)

## Schedule
*   **Daily Trigger Time**: 21:23 UTC daily (`23 21 * * *` in `daily_newsletter.yml`), offset ~5 hours earlier to absorb runner queue delays and dispatch by ~08:00 AM IST.
*   **Weekly Cleanup Schedule**: 00:00 UTC every Sunday (`0 0 * * 0` in `weekly_cleanup.yml`) to reset `history/featured_articles.json` while keeping `history/featured_repos.json` intact.

## Required Inputs & Environment
Ensure the following variables are configured in `.env` or GitHub Secrets:
- `PERPLEXITY_API_KEY`: API Key for Perplexity AI.
- `TAVILY_API_KEY`: (Optional) API Key for Tavily Live Web Search.
- `RECIPIENT_EMAIL`: Single email address or comma-separated list of recipients.
- `GMAIL_SMTP_EMAIL`: Sender email address for SMTP.
- `GMAIL_SMTP_PASSWORD`: Sender App Password for SMTP.
- `GITHUB_TOKEN`: Provided automatically in GitHub Actions for GitHub REST API authentication.

## Execution Sequence

```mermaid
graph TD
    A[Start] --> B[Fetch News Feeds tools/fetch_news.py]
    B --> C[Fetch Live Business Search tools/fetch_tavily.py]
    C --> D[Fetch Repo Candidates tools/fetch_repos.py]
    D --> E[Load Prompt Template & AI Synthesis tools/ai_research.py]
    E --> F[Generate Premium HTML Template tools/generate_html.py]
    F --> G{Is Dry Run?}
    G -- Yes --> H[Print Preview HTML Path]
    G -- No --> I[Dispatch Email to Recipients tools/send_email.py]
    I --> J[Commit History & End]
```

### 1. Raw News Retrieval
*   **Script**: `tools/fetch_news.py`
*   **Function**: Queries Hacker News (top, new, show) and curated AI/tooling RSS feeds.
*   **Output**: Saves `raw_news.json` in `.tmp/`.

### 2. GitHub Repository Candidate Retrieval
*   **Script**: `tools/fetch_repos.py`
*   **Function**: Queries GitHub REST Search API for trending AI/LLM repos and devtools, excluding repos featured within the last 60 days.
*   **Output**: Saves `raw_repos.json` in `.tmp/`.

### 3. AI Synthesis & Filtering
*   **Script**: `tools/ai_research.py`
*   **Function**: Uses Perplexity API (`sonar`) with structured `json_schema` to synthesize candidates across the 5 sections. Validates repo data and updates `history/featured_repos.json` and `history/featured_articles.json`.
*   **Output**: Saves `synthesized_news.json` in `.tmp/`.

### 4. HTML Rendering
*   **Script**: `tools/generate_html.py`
*   **Function**: Generates responsive table structure formatted for Gmail and Outlook, skipping empty sections.
*   **Output**: Saves `newsletter.html` in `.tmp/`.

### 5. Dispatch / Dry-Run
*   **Script**: `tools/send_email.py`
*   **Function**: Authenticates via Gmail SMTP and transmits HTML payload to all envelope recipients (To: sender). Exits non-zero if synthesized JSON contains zero items.

---

## Error Handling & Troubleshooting

*   **API Failure / Empty Response**: If Perplexity API fails or returns zero items, `ai_research.py` exits with status code 1. The pipeline halts immediately and no email is sent.
*   **Missing Credentials**: Missing `PERPLEXITY_API_KEY`, `RECIPIENT_EMAIL`, or SMTP credentials will cause the respective tool to print a critical error and exit non-zero.
*   **Dry-Run Mode**: Passing `--dry-run` to `run_newsletter.py` generates `.tmp/newsletter.html` without triggering `send_email.py`.

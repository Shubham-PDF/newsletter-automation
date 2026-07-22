# BUILDR.ai Daily Tech Briefing Compiler

`BUILDR.ai` is an automated, real-time technical news compilation and delivery engine designed specifically for software developers, systems engineers, and technology builders. 

Every day, the system parses high-signal technical sources, uses search-grounded AI compilation to analyze and synthesize the findings into five structured developer sections, and dispatches a clean, brand-grade HTML email directly to your inbox.

---

##  Why BUILDR.ai is Different

Most technical newsletters are either hand-curated (lagging behind) or fully automated RSS dumps (resulting in low-signal noise, duplicate items, and ads). 

`BUILDR.ai` bridges this gap with 5 focused sections:

1. **Launches** — New AI models, tools, products, APIs, and notable version releases with explicit developer task breakdowns.
2. **Prompting & Technique** — Practical, applicable techniques for getting better results out of models (concrete patterns, not theory).
3. **Head to Head** — Comparisons between models or tools: benchmarks, pricing, context limits, real-world tradeoffs, and "use X when Y" guidance.
4. **Tech Shifts** — Broader changes worth knowing about: infrastructure, deprecations, pricing moves, and regulation with practical developer impact.
5. **Repo Radar** — High-signal open-source developer repositories and CLI tools fetched directly via the GitHub REST API, complete with star counts, language tags, real-world use cases, and getting started commands.

### Core Architecture Features
- **Search-Grounded AI Synthesis**: Leverages the **Perplexity API (`sonar`)** to conduct real-time web searches alongside parsed feeds, verifying facts and pulling in breaking news from the last 24 hours.
- **GitHub REST Search & Repo Radar**: Automatically queries trending AI/LLM repos and developer productivity tools, enforcing a 60-day history exclusion window (`history/featured_repos.json`).
- **Strict Error Safety**: Fails non-zero immediately on missing API keys, network failures, or empty responses, preventing blank emails from ever being dispatched.
- **No Hallucinated Links**: Copies exact, verified URLs and repository star counts—no broken links or fabricated metadata.
- **Multi-Recipient Support**: Supports single or comma-separated email lists in `RECIPIENT_EMAIL` with envelope dispatch so recipients do not see each other's addresses.
- **Developer-First Typography & Aesthetic**: Built with inline CSS table layouts for Gmail and Outlook compatibility, featuring **Plus Jakarta Sans** and **JetBrains Mono**.

---

##  Project Structure

Following a structured, modular design:
*   `.github/workflows/`: Contains the daily Cron automation configurations (`30 2 * * *` = 08:00 AM IST) for GitHub Actions.
*   `tools/`: Python scripts executing deterministic actions (`fetch_news.py`, `fetch_repos.py`, `ai_research.py`, `generate_html.py`, `send_email.py`).
*   `history/`: Tracks previously featured repositories (`featured_repos.json`) and article URLs (`featured_articles.json`) to prevent repeats.
*   `workflows/`: Standard operating procedures and execution sequence outlines.
*   `.tmp/`: Gitignored local folder used during pipeline runs to store intermediate outputs (`raw_news.json`, `raw_repos.json`, `synthesized_news.json`, `newsletter.html`).

---

## Quick Start (Local Setup)

To test and run the project locally, follow these steps:

### 1. Clone & Set Up Virtual Environment
Initialize your local Python environment:
```bash
# Clone the repository and navigate to it
cd Newsletter

# Create a virtual environment
python3 -m venv .venv

# Activate the virtual environment
source .venv/bin/activate

# Install the required dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Create a `.env` file in the root directory:
```env
# Perplexity API Key for live search synthesis
PERPLEXITY_API_KEY=your_perplexity_api_key_here

# Recipient Email Config (supports single or comma-separated list)
RECIPIENT_EMAIL=recipient1@gmail.com, recipient2@gmail.com

# SMTP Gmail Config
GMAIL_SMTP_EMAIL=your_sender_gmail@gmail.com
GMAIL_SMTP_PASSWORD=your_16_character_app_password

# (Optional locally) GitHub Personal Access Token for higher API rate limits
GITHUB_TOKEN=your_github_token_here
```
> **Note**: The `GMAIL_SMTP_PASSWORD` must be a **16-character App Password** generated under your Google Account Security settings.

### 3. Run the Pipeline
Run the orchestrator command:
```bash
# Runs the full compile pipeline and sends the email
python run_newsletter.py

# Run in dry-run mode (safely builds newsletter.html in .tmp/ without sending email)
python run_newsletter.py --dry-run
```

---

## Getting the Newsletter Everyday (Automated Deployment)

You can set up `BUILDR.ai` to run completely for free every morning using GitHub Actions.

### 1. Push to GitHub
Push this repository to your private or public GitHub account.

### 2. Add Repository Secrets
On GitHub, go to your repository **Settings** > **Secrets and variables** > **Actions** and add the following secrets:
*   `PERPLEXITY_API_KEY`
*   `RECIPIENT_EMAIL` (single address or comma-separated list)
*   `GMAIL_SMTP_EMAIL`
*   `GMAIL_SMTP_PASSWORD`

> **Note**: GitHub automatically provides `GITHUB_TOKEN` to the workflow with no manual setup needed.

### 3. Done!
The workflow is configured in [.github/workflows/daily_newsletter.yml](file:///.github/workflows/daily_newsletter.yml) to execute every morning at **02:30 UTC (08:00 AM IST)** and automatically commit featured repository history back to the repo.

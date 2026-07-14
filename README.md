# BUILDR.ai Daily Tech Briefing Compiler

`BUILDR.ai` is an automated, real-time technical news compilation and delivery engine designed specifically for software developers, systems engineers, and technology builders. 

Every day, the system parses high-signal technical sources, uses search-grounded AI compilation to analyze and synthesize the findings, and dispatches a clean, brand-grade HTML email directly to your inbox.

---

##  Why BUILDR.ai is Different

Most technical newsletters are either hand-curated (meaning they lag behind and are limited to a single curator's feed) or fully automated RSS feeds (resulting in low-signal noise, duplicate items, and ads). 

`BUILDR.ai` bridges this gap:

1. **Search-Grounded AI Synthesis**: Unlike generic LLM summarizers, it leverages the **Perplexity API (`sonar`)** to conduct real-time web searches alongside parsed feeds, verifying facts and pulling in breaking news from the last 24 hours.
2. **Hybrid Curation Model**: It feeds raw candidates from a mix of **Hacker News (Top & New submissions)**, **arXiv Computer Science preprints (Networking, Systems, AI)**, and **TechCrunch** into the compilation engine, merging community-curated signal with academic depth and startup trends.
3. **No Hallucinated Links**: The engine copies exact, verified URLs from the source candidate feed or live search citations—no broken links.
4. **Developer-First Typography & Aesthetic**: The emails are designed with premium, minimalist layout principles. It imports custom typography (**Plus Jakarta Sans** and **JetBrains Mono** for technical code/deep-dives) and breaks down each topic into three structured points: **Overview**, **Technical Deep-Dive**, and **Why it Matters**.
5. **Headless & Serverless Out of the Box**: Zero database or server hosting required. It is pre-configured to run entirely inside a free GitHub Actions workflow.

---

##  Project Structure

Following a structured, modular design:
*   `.github/workflows/`: Contains the daily Cron automation configurations for GitHub Actions.
*   `tools/`: Python scripts executing deterministic actions (fetching, synthesis, HTML generation, email sending).
*   `workflows/`: Standard operating procedures and execution sequence outlines.
*   `.tmp/`: Gitignored local folder used during pipeline runs to store intermediate outputs (`raw_news.json`, `synthesized_news.json`, `newsletter.html`).

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
Create a `.env` file in the root directory (based on the template provided):
```env
# Perplexity API Key for live search synthesis
PERPLEXITY_API_KEY=your_perplexity_api_key_here

# Recipient Email Config
RECIPIENT_EMAIL=your_personal_inbox@gmail.com

# SMTP Gmail Config
GMAIL_SMTP_EMAIL=your_sender_gmail@gmail.com
GMAIL_SMTP_PASSWORD=your_16_character_app_password
```
> **Note**: The `GMAIL_SMTP_PASSWORD` must be a **16-character App Password** generated under your Google Account Security settings, not your main login password.

### 3. Run the Pipeline
Run the orchestrator command:
```bash
# Runs the full compile pipeline and sends the email
python run_newsletter.py

# Run in dry-run mode (safely builds newsletter.html in .tmp/ for layout preview)
python run_newsletter.py --dry-run
```

---

## Getting the Newsletter Everyday (Automated Deployment)

You can set up `BUILDR.ai` to run completely for free every morning using GitHub Actions.

### 1. Push to GitHub
Initialize git (if not already done) and push this repository to your private GitHub account:
```bash
git add .
git commit -m "Initial commit of BUILDR.ai newsletter pipeline"
git branch -M main
git remote add origin <your-github-repo-url>
git push -u origin main
```

### 2. Add Repository Secrets
On GitHub, go to your repository **Settings** > **Secrets and variables** > **Actions** and add the following four secrets:
*   `PERPLEXITY_API_KEY`
*   `RECIPIENT_EMAIL`
*   `GMAIL_SMTP_EMAIL`
*   `GMAIL_SMTP_PASSWORD`

### 3. Done!
The workflow is already configured in [.github/workflows/daily_newsletter.yml](file:///.github/workflows/daily_newsletter.yml) to execute every morning at **6:00 AM UTC** (which you can modify in the cron syntax to target your specific timezone). 

You can also trigger it manually at any time by going to the **Actions** tab in your GitHub repository, selecting the **Daily Technical Newsletter** workflow, and clicking **Run workflow**.

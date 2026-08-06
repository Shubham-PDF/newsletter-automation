# BUILDR.ai Daily Tech Briefing Compiler

`BUILDR.ai` is an automated, real-time technical news collection, deduplication, ranking, and AI synthesis engine built for software developers, AI automation engineers, and solution architects.

Every day, the pipeline ingests raw technical feeds, web searches, and model API snapshots, enforces strict recency and factual deduplication in Python, synthesizes high-signal insights via a Two-Stage LLM architecture (Editor -> Writer), and dispatches a brand-grade HTML briefing.

---

## Key Architecture & Features

1. **Deterministic Python Fact Layer**:
   - **Shared Item Contract (`tools/common.py`)**: All data sources normalize to a strict `Item` schema.
   - **Strict 30-Hour Recency Window**: Timezone-aware date parsing (`parse_dt`) rejects stale dates, future dates, and unparseable timestamps.
   - **Multi-Factor Ranking Formula**: Composite scoring balances keyword relevance, recency decay (`exp(-age/12)`), source authority, and cluster size.
   - **Jaccard Title Clustering (>= 0.55)**: Collapses near-duplicate headlines across tech press feeds into representative clusters.

2. **Source Registry & Verification (`sources.yaml` / `tools/verify_sources.py`)**:
   - Data collection is entirely driven by `sources.yaml`.
   - `verify_sources.py` validates all feeds, outputting `docs/source_health.md` and disabling non-200/empty endpoints.

3. **Repo Radar with Star Velocity & Quality Filters (`tools/fetch_repos.py`)**:
   - Quality filters reject null licenses, null languages, stale pushes (>30d), abnormal star ratios, and `NAME_BLOCK` patterns (`awesome-`, `interview`, `tutorial`).
   - Automated regex extraction of `install_hint` directly from repository READMEs.
   - 7-day star velocity ranking (`store.star_velocity`) tracks fast-growing repositories.

4. **Two-Stage AI Synthesis & Factual Grounding (`tools/ai_research.py`)**:
   - **Stage 1 (Editor Call)**: Evaluates top 60 candidate metadata rows and selects ~12-15 items across 5 sections.
   - **Enrichment**: Trafilatura fetches full article content ONLY for selected items, capping text at 700 words and re-verifying publication dates from article metadata.
   - **Stage 2 (Writer Call)**: Generates developer prose without receiving URLs, dates, or source names.
   - **Hydration (`ID_MAP`)**: Python hydrates exact URLs, titles, and sources back onto LLM output, enforcing zero cross-section duplicates and zero hallucinated URLs.

5. **SQLite-over-JSONL Persistence Layer (`tools/db.py`)**:
   - SQLite is rebuilt in memory at run start from `history/*.jsonl` files, ensuring diffable git history while providing full SQL query power.
   - TTL pruning automatically expires items at 30 days and featured items at 365 days.

---

## Project Structure

```
├── sources.yaml               # Source registry (RSS, Algolia, OpenRouter, HF, GitHub)
├── docs/
│   └── source_health.md       # Automated source health report
├── history/
│   ├── items.jsonl            # Ingested item deduplication log (30-day TTL)
│   ├── featured.jsonl         # Newsletter featured items log (365-day TTL)
│   ├── repo_stars.jsonl       # Repo star snapshot log (120-day TTL)
│   └── runs.jsonl             # Pipeline execution telemetry manifest
├── prompts/
│   ├── editor_system.txt      # Stage 1 Editor role prompt
│   ├── editor_user.txt        # Stage 1 Candidate selection template
│   ├── writer_system.txt      # Stage 2 Writer role prompt
│   └── writer_user.txt        # Stage 2 Section synthesis template
├── tools/
│   ├── common.py              # Shared dataclasses, date parser, relevance scorer, HTTP client
│   ├── db.py                  # SQLite-over-JSONL Store implementation
│   ├── verify_sources.py      # Source endpoint health verifier
│   ├── fetch_news.py          # Stages 1-5 Collection, Filtering, Clustering & Ranking
│   ├── fetch_repos.py         # GitHub Repo Radar with star velocity & install hint extraction
│   ├── fetch_tavily.py        # Tavily live web search collector (15 vertical queries)
│   ├── fetch_perplexity.py    # Perplexity sonar citation URL extractor
│   ├── ai_research.py         # Two-stage AI synthesis & ID_MAP hydration engine
│   ├── generate_html.py       # HTML template compiler
│   └── send_email.py          # Email SMTP dispatcher
├── tests/                     # Pytest suite covering WP-1 through WP-9
├── run_newsletter.py          # Pipeline orchestration script
└── requirements.txt           # Python dependency pins
```

---

## Quick Start (Local Execution)

```bash
# 1. Activate Virtual Environment & Install Dependencies
source .venv/bin/activate
pip install -r requirements.txt

# 2. Run Test Suite
PYTHONPATH=. pytest tests/

# 3. Verify Source Health
python tools/verify_sources.py

# 4. Execute Full Pipeline (Dry-Run Mode)
python run_newsletter.py --dry-run
```

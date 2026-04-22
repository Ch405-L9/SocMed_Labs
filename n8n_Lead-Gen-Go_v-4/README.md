# ICP Lead Generation System
### Human-in-the-Loop Pipeline for Local Business Outreach

**Version:** 1.4.0 | **Platform:** Ubuntu Linux | **Python:** 3.11+  
**License:** MIT | **Author:** BADGR Technologies LLC

---

A fully local, open-source pipeline that collects local business leads, enriches them with live website signals, scores them against an Ideal Customer Profile (ICP) model, and routes them through human review before committing final output. Designed for independent healthcare provider outreach starting from ZIP code 30350 (Sandy Springs / Dunwoody, GA), with support for any ZIP code and business category.

No paid APIs. No cloud dependencies. Runs entirely on-premise with Ollama local LLMs.

---

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Project Structure](#project-structure)
3. [Prerequisites](#prerequisites)
4. [Installation](#installation)
5. [Running the Pipeline](#running-the-pipeline)
6. [Human Review](#human-review)
7. [Outreach Cadence Tracker](#outreach-cadence-tracker)
8. [Web Dashboard](#web-dashboard)
9. [Weight Calibration](#weight-calibration)
10. [Visualization](#visualization)
11. [Configuration Reference](#configuration-reference)
12. [ICP Scoring Model](#icp-scoring-model)
13. [Ollama LLM Integration](#ollama-llm-integration)
14. [n8n Orchestration (Optional)](#n8n-orchestration-optional)
15. [Supported Categories](#supported-categories)
16. [Troubleshooting](#troubleshooting)

---

## System Architecture

```
ZIP Code + Category Input
          |
          v
    [ COLLECTOR ]
    search.py
    DuckDuckGo HTML search (no API key)
    Output: data/raw_leads.json
          |
          v
    [ CRAWLER ]
    fetch.py + trafilatura
    Website reachability, booking signals,
    SEO metadata, social links, HTTPS status
    Output: data/enriched_leads.json
          |
          v
    [ ICP SCORING ENGINE ]
    icp_model.py (deterministic weights)
    prompt_engine.py (Ollama LLM reasoning)
    Output: data/scored_leads_full.json
          |
          v
    [ HUMAN REVIEW CLI ]
    review_cli.py
    Approve / Modify score / Reject / Skip
    Stores decisions to SQLite
          |
          v
    [ STORAGE + EXPORT ]
    db.py + schema.sql
    SQLite database, CSV export
    Output: data/scored_leads.csv, data/leads.db
          |
          v
    [ VISUALIZATION ]
    dashboard.py
    matplotlib + seaborn charts
    Output: viz/output/*.png, leads_summary.html
```

---

## Project Structure

```
n8n-icp-stack/
├── apps/
│   ├── collector/
│   │   ├── search.py           DuckDuckGo search and lead extraction
│   │   ├── sources.py          Category queries, booking/SEO/social signal definitions
│   │   └── gbp.py              Google Business Profile signal extraction (no API key)
│   ├── crawler/
│   │   ├── fetch.py            HTTP crawling, enrichment, incremental cache, contact extraction
│   │   └── render.py           Optional Playwright renderer for JS-heavy/blocked pages
│   ├── scoring/
│   │   ├── icp_model.py        Deterministic 0-100 ICP scoring engine
│   │   └── prompt_engine.py    Ollama API integration, Jinja2 prompt templates, fallback logic
│   ├── human_loop/
│   │   ├── review_cli.py       Interactive terminal review tool
│   │   └── cadence_cli.py      Outreach cadence tracker and follow-up logger
│   └── storage/
│       ├── db.py               SQLite CRUD, CSV export, view queries, calibration reads
│       └── schema.sql          Database schema, outreach_log table, leads_full view
├── config/
│   ├── config.yaml             Central configuration for all modules
│   ├── zcta_centroids.csv      Atlanta metro ZIP centroid lat/lon for radius expansion
│   └── prompts/
│       ├── scoring_v1.j2       Jinja2 scoring prompt template (v1 — generic ICP)
│       ├── scoring_v2.j2       Jinja2 scoring prompt template (v2 — 5-dimension Healthcare Lead Leak Scan) ← active
│       ├── reasoning_v1.j2     Jinja2 reasoning summary prompt template (v1)
│       └── reasoning_v2.j2     Jinja2 reasoning summary prompt template (v2 — healthcare-specific) ← active
├── data/
│   ├── raw_leads.json          Collector output (unprocessed leads)
│   ├── enriched_leads.json     Crawler output (leads + website signals)
│   ├── scored_leads_full.json  Scoring output (leads + ICP scores + LLM reasoning)
│   ├── scored_leads.csv        Final human-reviewed export
│   ├── outreach_cadence.csv    Outreach log export
│   ├── calibrated_weights.json Suggested ICP weight adjustments (after calibrate step)
│   └── leads.db                SQLite database
├── templates/
│   ├── base.html               Dashboard base layout (no CDN dependencies)
│   ├── index.html              Lead table page with client-side filtering
│   ├── lead_detail.html        Full lead detail view
│   └── charts.html             Chart gallery page
├── keywords/
│   ├── keywords.py             SerpAPI-based Web-Ops discovery script (T0–T3 tiers, outreach templates, ICP classification)
│   ├── keywords.atl.north.json ATL north keyword set by intent category
│   ├── keywords.se.us.json     Southeast US keyword set by intent category
│   └── discovery/              Output directory for dated discovery CSVs
├── Lead Leaks and Web-Optimization Kit/
│   ├── HEALTHCARE_LEADS_REPORT_30350.md   Full ranked outreach report with email drafts
│   └── website_optimization_workflow.md  BADGR web optimization protocol
├── n8n/
│   └── workflows.json          n8n workflow (Cron + Webhook + Slack + Sheets + Email)
├── scripts/
│   ├── run_pipeline.py         Main orchestrator (collect/crawl/score/export/calibrate/deduplicate)
│   ├── serve_dashboard.py      FastAPI read-only web dashboard server
│   └── sync_data.py            Data file synchronization utility
├── viz/
│   ├── dashboard.py            Chart generation script
│   └── output/                 Generated PNG charts and HTML summary table
├── CHANGELOG.md
├── FUTURE_DEV.md
├── INSTRUCTIONS.md
├── Dockerfile.python
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## Prerequisites

### Required

| Dependency | Version | Purpose |
|------------|---------|---------|
| Python | 3.11 or 3.12 | Runtime for all pipeline modules |
| pip | 23+ | Package installation |
| git | Any | Version control |

### Optional

| Dependency | Version | Purpose |
|------------|---------|---------|
| Ollama | Latest | Local LLM inference for reasoning summaries |
| Docker + Docker Compose | Latest | Container-based n8n + Ollama orchestration |
| Playwright | 1.40+ | JS-heavy website rendering (disabled by default) |

### Verify Python version

```bash
python3 --version
```

Output should be `Python 3.11.x` or `Python 3.12.x`.

---

## Installation

### Step 1 — Clone the repository

```bash
git clone <repository-url> n8n-icp-stack
cd n8n-icp-stack
```

### Step 2 — Create and activate a virtual environment

Creating a virtual environment is required on Ubuntu 24.04+ due to PEP 668 system package restrictions.

```bash
python3 -m venv .venv
source .venv/bin/activate
```

To confirm the environment is active, your terminal prompt will show `(.venv)`.

### Step 3 — Install Python dependencies

```bash
pip install -r requirements.txt
```

Expected output ends with: `Successfully installed ...`

### Step 4 — Verify installation

```bash
python3 -c "import requests, bs4, trafilatura, pandas, matplotlib, seaborn; print('All dependencies verified.')"
```

### Step 5 — (Optional) Install Ollama for LLM enrichment

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama serve
```

Pull the models used by the scoring engine:

```bash
ollama pull qwen2.5-coder:7b
ollama pull llama3.1:8b
ollama pull llama3.2:3b
ollama pull phi3:mini
```

---

## Running the Pipeline

All commands are run from the project root (`n8n-icp-stack/`) with the virtual environment active.

```bash
source .venv/bin/activate
```

---

### Option A — Full Pipeline (All Steps)

Runs collect, crawl, score, export, and visualization in sequence.

```bash
python scripts/run_pipeline.py
```

With LLM enrichment enabled (requires Ollama running):

```bash
python scripts/run_pipeline.py --ollama
```

With a different ZIP code and category:

```bash
python scripts/run_pipeline.py --zip 30305 --category dental --max 15
```

---

### Option B — Import an Existing CSV (Skip Collection)

If you already have a list of leads in a CSV file, import them directly without running DuckDuckGo searches.

```bash
python scripts/run_pipeline.py import --file path/to/leads.csv
```

With optional defaults for missing fields:

```bash
python scripts/run_pipeline.py import --file healthcare_leads_30350.csv --geo-area "30350" --category healthcare
```

Then continue with the crawl step:

```bash
python scripts/run_pipeline.py crawl
python scripts/run_pipeline.py score
```

**Accepted CSV column names** (case-insensitive, any order):

| Canonical Field | Accepted Column Names |
|----------------|-----------------------|
| `business_name` | Business Name, Name, Company, Company Name |
| `website` | Website URL, Website, URL, Site, Web |
| `category` | Category, Type, Business Type |
| `address` | Full Address, Address, Street, Location |
| `geo_area` | Geo Area, ZIP, Zip Code, City |
| `phone` | Phone, Phone Number, Telephone |
| `email` | Email, Email Address |

Rows are deduplicated against existing entries in `data/raw_leads.json` by business name and website URL. Duplicates are skipped without error.

---

### Option C — Run Individual Steps

#### Step 1: Collect leads

Searches DuckDuckGo for local businesses matching the ZIP code and category. Writes to `data/raw_leads.json`. New leads are appended; duplicates are skipped.

```bash
# Single ZIP
python scripts/run_pipeline.py collect --zip 30350 --category healthcare

# Multiple specific ZIPs (searched in sequence, cross-ZIP deduplication applied)
python scripts/run_pipeline.py collect --zips "30350,30342,30328,30338" --category healthcare

# All ZIPs within 10 miles of a center ZIP
python scripts/run_pipeline.py collect --center 30350 --radius 10

# 20-mile radius for wider territory
python scripts/run_pipeline.py collect --center 30350 --radius 20
```

Parameters:

| Flag | Default | Description |
|------|---------|-------------|
| `--zip` | `30350` | Single ZIP code to search near |
| `--zips` | — | Comma-separated list of ZIP codes |
| `--center` | — | Center ZIP for radius-based expansion |
| `--radius` | `10` | Search radius in miles (requires `--center`) |
| `--category` | `healthcare` | Business category (see Supported Categories) |
| `--max` | `10` | Maximum search results per query per ZIP |
| `--pause` | `1.5` | Seconds to pause between requests |

Radius expansion uses `config/zcta_centroids.csv` for Atlanta metro ZIP coordinates. Add additional rows to extend coverage to other metro areas.

#### Step 2: Crawl websites

Fetches each lead's website and extracts digital presence signals, phone numbers, and email addresses. Reads `data/raw_leads.json`, writes `data/enriched_leads.json`.

```bash
python scripts/run_pipeline.py crawl
```

With PageSpeed Insights scoring enabled (uses Google's free API tier):

```bash
python scripts/run_pipeline.py crawl --pagespeed
```

Parameters:

| Flag | Default | Description |
|------|---------|-------------|
| `--timeout` | `10` | HTTP request timeout in seconds |
| `--pause` | `1.5` | Seconds between requests |
| `--no-contacts` | off | Skip phone and email extraction |
| `--pagespeed` | off | Call PageSpeed Insights API per reachable site |
| `--pagespeed-key` | `""` | Google API key (optional; anonymous tier is ~400 req/day) |
| `--force-crawl` | off | Re-crawl all sites, bypassing the 7-day cache |
| `--crawl-window` | `7` | Days before a site is eligible for re-crawl |
| `--gbp` | off | Fetch Google Business Profile signals via DuckDuckGo |
| `--gbp-pause` | `2.5` | Seconds between GBP lookups |
| `--playwright` | off | Retry blocked (403) sites using headless Chromium |

**Incremental crawl:** By default, sites crawled within the past 7 days are skipped. The timestamp and a content hash are stored in `enriched_leads.json`. On the next crawl run, unchanged pages reuse the prior enrichment data. Use `--force-crawl` to bypass this cache entirely.

**Contact extraction** is on by default. The crawler pulls phone numbers from `tel:` links and visible page text, and email addresses from `mailto:` links and visible text. Email domains are verified against live MX records before inclusion.

**GBP signals** (`--gbp`): Searches DuckDuckGo for each business's Google Business Profile rating and review count. Adds `gbp_rating`, `gbp_review_count`, `gbp_verified`, and `gbp_unclaimed` to the enrichment dict. Unclaimed or zero-review practices receive additional ICP score points.

#### Step 3: Score leads

Applies the ICP scoring model to all enriched leads. Reads `data/enriched_leads.json`, writes `data/scored_leads_full.json`.

```bash
# Deterministic scoring only
python scripts/run_pipeline.py score

# Deterministic scoring + Ollama LLM reasoning
python scripts/run_pipeline.py score --ollama
```

#### Step 4: Export

Exports the reviewed dataset from SQLite to `data/scored_leads.csv`. If no SQLite data exists, exports directly from `scored_leads_full.json`.

```bash
python scripts/run_pipeline.py export
```

#### Step 5: Visualize

Generates all charts and the HTML summary table. Reads from available CSV or JSON sources.

```bash
python scripts/run_pipeline.py viz
```

Or run the dashboard script directly for chart selection:

```bash
python viz/dashboard.py --charts distribution category high_risk
```

Available chart options: `distribution`, `category`, `high_risk`, `correlation`, `review`, `all`

#### Step 6 (optional): Deduplicate

Deduplication runs automatically during `collect`, but can also be run manually to clean up accumulated duplicates:

```bash
python scripts/run_pipeline.py deduplicate
```

Matches by name similarity (> 85% via `difflib`) and shared address prefix, or exact website URL. Reports how many records were removed.

#### Step 7 (optional): Calibrate ICP weights

After human review decisions accumulate, run calibration to generate suggested weight adjustments based on how your overrides differed from the model's scores:

```bash
python scripts/run_pipeline.py calibrate

# Lower threshold (default: 5 overrides minimum)
python scripts/run_pipeline.py calibrate --min-overrides 3
```

Output: `data/calibrated_weights.json` — a suggested replacement for the `scoring.weights` block in `config/config.yaml`. The command prints a before/after table and never auto-applies changes unless `calibration.auto_apply: true` is set in config.

---

### Skipping the Crawl Step

If you already have enriched or analyzed data and want to skip re-crawling:

```bash
python scripts/run_pipeline.py score
python scripts/run_pipeline.py export
python scripts/run_pipeline.py viz
```

The scoring engine automatically falls back through this file priority:
1. `data/enriched_leads.json`
2. `data/raw_leads.json`
3. `data/analyzed_leads.json`

---

## Human Review

The review CLI presents each scored lead in the terminal with full signal data, the ICP score, and LLM reasoning. The reviewer approves, modifies, rejects, or skips each lead before the result is committed to the database.

### Launch the review session

```bash
python apps/human_loop/review_cli.py --input data/scored_leads_full.json
```

### Review controls

| Key | Action | Effect |
|-----|--------|--------|
| A | Approve | Accept the model's score as-is; mark as human-verified |
| M | Modify | Enter a new score (0-100) and note the reason |
| R | Reject | Set score to 0; exclude from priority outreach |
| S | Skip | Pass this lead; it remains unreviewed in the database |
| Q | Quit | Save progress and exit; resume later with `--from N` |

### Resume an interrupted session

```bash
python apps/human_loop/review_cli.py --input data/scored_leads_full.json --from 12
```

### Review only pending (un-reviewed) leads from the database

```bash
python apps/human_loop/review_cli.py --pending
```

Human decisions are stored in `data/leads.db`. The `final_score` column in all exports reflects any human override. Override history is preserved and never destructively updated.

---

## Outreach Cadence Tracker

The cadence CLI tracks contact attempts, responses, and follow-up schedules per lead. All data is stored in the `outreach_log` table in `data/leads.db`.

```bash
python apps/human_loop/cadence_cli.py <command> [options]
```

### Commands

#### List all leads with outreach status

```bash
python apps/human_loop/cadence_cli.py list
```

Displays a color-coded table with ICP score, contact attempt count, last contact date, next follow-up date (red if overdue), and last recorded response.

#### Log a contact attempt

```bash
# Interactive (prompts for channel, response, notes, follow-up date)
python apps/human_loop/cadence_cli.py log 5

# Non-interactive with flags
python apps/human_loop/cadence_cli.py log 5 \
  --channel email \
  --response interested \
  --contact-person "Dr. Patel (front desk)" \
  --notes "Replied within 2 hours, wants a call back" \
  --follow-up 2026-04-30
```

| Flag | Options | Description |
|------|---------|-------------|
| `--channel` | email, phone, walk_in, linkedin, other | How contact was made |
| `--response` | no_response, interested, not_interested, scheduled, bounced | Lead's response |
| `--contact-person` | any string | Name or role of the person contacted |
| `--notes` | any string | Free-form notes about the interaction |
| `--follow-up` | YYYY-MM-DD | Schedule a follow-up reminder |

#### Show overdue follow-ups

```bash
python apps/human_loop/cadence_cli.py followups
```

Lists all leads where `follow_up_date` is on or before today and the response is still `no_response`. Override the reference date:

```bash
python apps/human_loop/cadence_cli.py followups --date 2026-05-01
```

#### Show full history for a lead

```bash
python apps/human_loop/cadence_cli.py history 5
```

Displays all contact log entries for lead ID 5 in chronological order with channel, response, notes, and follow-up date.

#### Update a log entry's response

```bash
python apps/human_loop/cadence_cli.py update 12 --response scheduled --notes "Booked intro call for May 3"
```

#### Export cadence log to CSV

```bash
python apps/human_loop/cadence_cli.py export
# Output: data/outreach_cadence.csv

python apps/human_loop/cadence_cli.py export --out reports/april_cadence.csv
```

The exported CSV joins leads, enrichment (phone/email), scores, and the full outreach log for use in external reporting tools.

---

## Web Dashboard

A read-only FastAPI web interface lets you browse, filter, and export leads from a browser — no terminal required for non-technical stakeholders.

### Launch

```bash
source .venv/bin/activate
python scripts/serve_dashboard.py
```

Open **http://127.0.0.1:8080** in any browser.

### Pages

| Route | Description |
|-------|-------------|
| `/` | Filterable lead table with score bars and risk badges |
| `/lead/<id>` | Full lead detail: score, signals, contact info, GBP, outreach history |
| `/charts` | All `viz/output/` PNG charts |
| `/export` | Download `scored_leads.csv` |
| `/api/leads` | JSON endpoint — all leads |
| `/api/lead/<id>` | JSON endpoint — single lead |

### Options

```bash
python scripts/serve_dashboard.py --port 9090          # Different port
python scripts/serve_dashboard.py --host 0.0.0.0       # LAN accessible
python scripts/serve_dashboard.py --db other/leads.db  # Custom database
```

Requires `fastapi`, `uvicorn`, and `jinja2` (included in `requirements.txt`).

---

## Weight Calibration

After accumulating human review overrides, the calibration step analyzes how your scores differed from the model's and suggests adjusted weights.

```bash
python scripts/run_pipeline.py calibrate
```

Output is written to `data/calibrated_weights.json`. The command prints a before/after comparison table to the terminal. Weights are never auto-applied unless `calibration.auto_apply: true` is set in `config/config.yaml`.

To apply: copy the suggested values into the `scoring.weights` section of `config/config.yaml` and re-run `score`.

---

## Visualization

Charts are generated from whatever scored data is available. The script loads sources in this priority order: `data/scored_leads.csv` → `data/scored_leads_full.json` → `data/enriched_leads.json` → `data/healthcare_leads_30350.csv`.

```bash
python viz/dashboard.py
```

Output files in `viz/output/`:

| File | Description |
|------|-------------|
| `01_score_distribution.png` | ICP score histogram with risk band breakdown |
| `02_category_breakdown.png` | Average ICP score and lead count by business category |
| `03_high_priority_leads.png` | Horizontal bar chart of highest-scoring leads |
| `04_digital_presence_correlation.png` | Signal correlation matrix and scatter plot |
| `05_review_summary.png` | Human review decision pie chart and verification status |
| `leads_summary.html` | Full sortable HTML table of all leads |

---

## Configuration Reference

All system parameters are controlled from `config/config.yaml`. No environment variables or hardcoded values are used in the pipeline modules.

```yaml
search:
  default_zip: "30350"          # Default ZIP code for lead collection
  default_category: "healthcare" # Default business category
  max_results: 30               # Max leads to collect per run
  ddg_pause_seconds: 2          # Pause between DuckDuckGo requests

crawler:
  timeout: 10                   # HTTP request timeout in seconds
  max_retries: 2                # Retry attempts on connection failure
  user_agent: "Mozilla/5.0..."  # Browser user agent string
  use_playwright: false         # Enable JS rendering (requires playwright install)

ollama:
  base_url: "http://localhost:11434"
  scoring_model: "qwen2.5-coder:7b"   # Model for structured JSON analysis
  reasoning_model: "llama3.1:8b"      # Model for natural language summaries
  fallback_model: "phi3:mini"          # Used if preferred models unavailable
  timeout: 60                          # Inference timeout in seconds
  enabled: true                        # Set false to disable LLM enrichment globally

scoring:
  weights:
    website_missing: 30         # Points added when site is unreachable
    no_booking: 15              # Points added when no booking system detected
    weak_seo: 20                # Points added when SEO metadata is absent
    no_social: 10               # Points added when no social links found
    independent_practice: 15   # Points added for non-chain practices
    strong_digital_maturity: -20  # Points deducted when all signals are strong
  risk_thresholds:
    high: 70                    # Score >= 70 classified as high
    medium: 40                  # Score 40-69 classified as medium

storage:
  data_dir: "data"
  raw_leads: "data/raw_leads.json"
  enriched_leads: "data/enriched_leads.json"
  scored_leads: "data/scored_leads.csv"
  sqlite_db: "data/leads.db"
  use_sqlite: true

viz:
  output_dir: "viz/output"
  dpi: 150
  style: "seaborn-v0_8-darkgrid"

n8n:
  webhook_url: "http://localhost:5678/webhook/icp-trigger"
  enabled: false
```

---

## ICP Scoring Model

The ICP scoring engine (`apps/scoring/icp_model.py`) assigns a 0-100 opportunity score to each lead. A higher score indicates a stronger ICP fit — meaning the lead has more digital gaps that the agency can address.

### Scoring weights

| Signal | Condition | Points |
|--------|-----------|--------|
| Website status | Missing, DNS failed, connection error | +30 |
| Website status | Blocked (403), timeout, SSL error | +21 |
| Booking system | No booking link or platform detected | +15 |
| SEO metadata | No title tag or meta description | +20 |
| Social presence | No social links found | +10 |
| Social presence | One platform only | +5 |
| Practice type | Independent (non-chain) signals | +15 |
| Digital maturity | Booking + SEO + 2+ social platforms | -20 |
| PageSpeed (mobile) | Performance score below 50 | +10 |
| PageSpeed (mobile) | Performance score 50-69 | +5 |
| GBP status | Unclaimed or no listing detected | +10 |
| GBP reviews | Zero Google reviews | +5 |
| GBP rating | Rating below 3.5 stars | +5 |

PageSpeed signals are only scored when `--pagespeed` is passed during crawl. GBP signals require `--gbp`. Both are optional; leads without these measurements receive 0 points for those signals and are not penalized.

### Risk classification

| Level | Score Range | Recommended Action |
|-------|-------------|-------------------|
| High | 70 - 100 | Immediate outreach — multiple critical gaps |
| Medium | 40 - 69 | Targeted outreach — specific addressable gaps |
| Low | 0 - 39 | Monitor — practice has solid digital foundation |

### Score reasoning structure

Each scored lead includes a `reasoning` JSON object detailing which signals fired and the points contributed. This feeds directly into the human review CLI display and the Ollama prompt context.

---

## Ollama LLM Integration

When the `--ollama` flag is passed to the scoring step, the pipeline calls locally running Ollama models to generate two outputs per lead:

**Structured JSON analysis** (via `qwen2.5-coder:7b`, template `scoring_v2.j2`):
- Opportunity summary (2-3 sentences grounded in signal data)
- Top pain points (list tied to specific dimensions)
- Recommended services (list)
- Outreach angle (single actionable sentence)
- `lead_leak_dimensions` — 5-dimension Healthcare Lead Leak Scan result:
  - `speed_mobile` — PageSpeed and site weight assessment
  - `intake_booking` — Patient booking funnel completeness
  - `tracking_visibility` — Analytics, GBP, and SEO signal quality
  - `compliance_trust` — ADA, HIPAA patterns, trust signals
  - `message_clarity` — 5-second clarity of who, what, and next step
- Confidence rating

Each dimension returns `pass`, `needs_work`, `failing`, or `unknown` based on enrichment data already present — no additional API calls.

**Natural language reasoning summary** (via `llama3.1:8b`, template `reasoning_v2.j2`):
- 2-3 sentence outreach-ready summary naming the most critical gap and ending with a first-contact hook; framed in patient acquisition or compliance terms rather than generic tech language

If Ollama is not running or no models are available, the system falls back to deterministic text generation based on the scoring signal flags. All pipeline steps complete regardless of Ollama availability.

### Model preference order

The engine queries Ollama for available models and selects from this priority list:

1. `qwen2.5-coder:7b` — structured JSON output
2. `llama3.1:8b` — reasoning summaries
3. `llama3.2:3b` — fallback for both
4. `phi3:mini` — last resort

---

## n8n Orchestration (Optional)

n8n provides a visual workflow interface for automating the full pipeline with scheduled runs, Slack notifications, Google Sheets sync, and email alerts.

### Start the stack

```bash
docker-compose up -d
```

This starts three services:

| Service | URL | Credentials |
|---------|-----|-------------|
| n8n | http://localhost:5678 | admin / admin123 |
| Ollama | http://localhost:11434 | No auth required |
| Python runner | Internal | Container exec |

### Import the workflow

1. Open http://localhost:5678 in a browser
2. Navigate to: **Workflows → Import from File**
3. Select `n8n/workflows.json`
4. Activate the workflow

### Trigger methods

**Scheduled (Cron):** The workflow includes a Cron node set to run nightly at 2:00 AM. Edit the node to change the schedule.

**Manual webhook:**

```bash
curl -X POST http://localhost:5678/webhook/icp-trigger \
  -H "Content-Type: application/json" \
  -d '{"zip_code": "30350", "category": "healthcare"}'
```

### Notification nodes

The workflow includes optional notification steps that activate when configured:

| Node | What it does | Config key |
|------|-------------|------------|
| Slack — High Priority | Posts Block Kit message when score ≥ 70 leads are found | `notifications.slack_webhook_url` |
| Slack — Standard | Posts lead count summary after every run | `notifications.slack_webhook_url` |
| Google Sheets Sync | Appends/updates scored_leads.csv rows in a sheet | `notifications.google_sheet_id` |
| Review Request Email | Emails formatted lead summary to reviewer | `notifications.reviewer_email` |

Set the relevant keys in `config/config.yaml` and configure matching n8n credentials. See [INSTRUCTIONS.md — Section 14](#14-n8n-notifications-setup) for step-by-step credential setup.

### Stop the stack

```bash
docker-compose down
```

Data persists in Docker volumes `n8n_data` and `ollama_data` between restarts.

---

## Web-Ops Discovery Pipeline (SerpAPI)

A separate keyword-driven discovery script (`keywords/keywords.py`) finds businesses by web-ops pain-point searches via Google Maps rather than healthcare category queries. It operates independently of the main pipeline and requires a SerpAPI key.

### Keyword tiers

| Tier | Intent level | Conversion probability |
|------|-------------|----------------------|
| T0 | Vendor switching pain — actively looking to leave a provider | Highest |
| T1 | Immediate pain — speed, compliance, conversion | 70-85% |
| T2 | Strategic ongoing needs | 50-70% |
| T3 | Retainer and recurring service intent | 40-60% |

### Web-Ops ICP classification

Every lead is automatically classified into a vertical (`legal`, `healthcare`, `financial`, `ecommerce_retail`, `real_estate`, `home_services`, `hospitality_food`, `professional_services`, `education`, `general`) with a `compliance_urgency` rating (`high`, `medium_high`, `medium`, `low`) based on the Google Maps business type. High-compliance verticals (legal, healthcare, financial) are flagged immediately for ADA, HIPAA, and PCI-focused outreach.

### Pre-loaded outreach copy

Each lead in the output CSV arrives with five outreach columns ready to use: `email_subject`, `email_opening`, `value_prop`, `cta`, and `urgency_angle`. Replace `[COMPANY]` with the lead's name at send time.

### Run

```bash
# Add SERPAPI_KEY to .env or .env-local, then:
cd keywords && python3 keywords.py
# Output: keywords/discovery/<date>_disc-leads.csv
```

---

## Supported Categories

| Key | Label | Queries Generated |
|-----|-------|-------------------|
| `healthcare` | All Healthcare | General healthcare provider queries |
| `primary_care` | Primary Care | Family medicine, internal medicine |
| `dental` | Dental | Dentist, cosmetic dentistry |
| `chiropractic` | Chiropractic | Chiropractor, spinal care |
| `urgent_care` | Urgent Care | Walk-in clinic, immediate care |
| `physical_therapy` | Physical Therapy | PT clinic, sports rehab |
| `specialty` | Specialty | Specialist physician, cardiology, dermatology |
| `wellness` | Wellness | Wellness center, holistic health |

To add a new category, add an entry to the `CATEGORY_QUERIES` dictionary in `apps/collector/sources.py`.

---

## Troubleshooting

### Virtual environment not recognized

Ensure the environment is activated before running any commands:

```bash
source .venv/bin/activate
which python3   # Should point to .venv/bin/python3
```

### "externally-managed-environment" error on pip install

This occurs on Ubuntu 24.04+ without a virtual environment. Create one first:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### No leads collected

DuckDuckGo HTML scraping may be rate-limited. Increase the pause between requests:

```bash
python scripts/run_pipeline.py collect --pause 4.0
```

If the issue persists, DuckDuckGo may be temporarily blocking the IP. Wait 10-15 minutes and retry.

### Ollama connection refused

Verify Ollama is running:

```bash
ollama serve         # Start the server if not running
curl http://localhost:11434/api/tags   # Should return model list JSON
```

If running inside Docker, ensure the container uses `http://ollama:11434` (service name), not `localhost`.

### Dashboard import error (seaborn style)

If `seaborn-v0_8-darkgrid` style is not available on older matplotlib versions:

```bash
pip install --upgrade matplotlib seaborn
```

The dashboard will fall back to `ggplot` style automatically if the preferred style is unavailable.

### SQLite database locked

If the pipeline errors with `database is locked`, another process may have the file open:

```bash
fuser data/leads.db   # Identify the process
```

Close the conflicting process or wait for it to complete, then retry.

---

## Related Files

| File | Description |
|------|-------------|
| `CHANGELOG.md` | Version history and release notes |
| `FUTURE_DEV.md` | Planned enhancements and architectural recommendations |
| `Lead Leaks and Web-Optimization Kit/HEALTHCARE_LEADS_REPORT_30350.md` | Full scored outreach report with email drafts |
| `Lead Leaks and Web-Optimization Kit/website_optimization_workflow.md` | BADGR web optimization and HIPAA outreach protocol |

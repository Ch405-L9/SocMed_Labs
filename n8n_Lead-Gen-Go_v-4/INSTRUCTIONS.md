# ICP Lead Generation System — Operator Instructions
### Step-by-Step Guide from First Run to Ongoing Outreach

**Version:** 1.4.0 | **Platform:** Ubuntu Linux | **Python:** 3.11+

---

## Table of Contents

1. [Initial Setup](#1-initial-setup)
2. [Full Pipeline — First Run](#2-full-pipeline--first-run)
3. [Running Individual Steps Manually](#3-running-individual-steps-manually)
4. [Importing Your Own Lead Lists](#4-importing-your-own-lead-lists)
5. [Human Review Session](#5-human-review-session)
6. [Outreach Cadence Tracking](#6-outreach-cadence-tracking)
7. [Expanding to New Geographies](#7-expanding-to-new-geographies)
8. [Updating the ICP Model](#8-updating-the-icp-model)
9. [Customizing Prompt Templates](#9-customizing-prompt-templates)
10. [Ongoing / Scheduled Runs](#10-ongoing--scheduled-runs)
11. [Viewing Results and Exports](#11-viewing-results-and-exports)
12. [Web Dashboard](#12-web-dashboard)
13. [Weight Calibration](#13-weight-calibration)
14. [n8n Notifications Setup](#14-n8n-notifications-setup)
15. [Quick Reference — All Commands](#15-quick-reference--all-commands)

---

## 1. Initial Setup

These steps are required once when setting up the project on a new machine.

### 1.1 Clone the project

```bash
cd ~
git clone <repo-url> n8n-icp-stack
cd n8n-icp-stack
```

### 1.2 Create and activate a virtual environment

Ubuntu 24.04+ blocks global `pip` installs. Always use a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

You will see `(.venv)` in your terminal prompt when the environment is active.
You must re-run `source .venv/bin/activate` each time you open a new terminal.

### 1.3 Install dependencies

```bash
pip install -r requirements.txt
```

This installs all required packages including BeautifulSoup, trafilatura, pandas, matplotlib, dnspython, and Jinja2.

### 1.4 Initialize the database

```bash
python3 -c "
import sys
sys.path.insert(0, 'apps/storage')
from db import init_db
init_db()
print('Database initialized.')
"
```

The database file is created at `data/leads.db`. This step is safe to run multiple times — it is non-destructive.

### 1.5 Install Ollama (optional, for LLM enrichment)

Ollama provides local AI-generated reasoning summaries for each lead. Skip this if you only want deterministic scoring.

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.1:8b
ollama pull qwen2.5-coder:7b
```

Verify Ollama is running:

```bash
curl http://localhost:11434/api/tags
```

---

## 2. Full Pipeline — First Run

Run all steps end-to-end in a single command. This collects leads, crawls their websites, scores them, exports to CSV, and generates charts.

```bash
source .venv/bin/activate
python3 scripts/run_pipeline.py
```

### Default behavior

- Searches DuckDuckGo for healthcare businesses near ZIP 30350
- Crawls up to 10 websites per search query
- Applies the ICP scoring model (deterministic, no Ollama needed)
- Exports results to `data/scored_leads.csv` and `data/leads.db`
- Generates charts to `viz/output/`

### Full pipeline with LLM enrichment

Requires Ollama running with at least one model installed:

```bash
python3 scripts/run_pipeline.py --ollama
```

### Full pipeline with all enrichment features enabled

```bash
python3 scripts/run_pipeline.py \
  --zip 30350 \
  --category healthcare \
  --max 15 \
  --ollama \
  --gbp \
  --pagespeed
```

This adds Google Business Profile signals (`--gbp`) and PageSpeed Insights scores (`--pagespeed`) to each lead.

---

## 3. Running Individual Steps Manually

Each pipeline step can be run independently. This is useful when you want to re-score without re-crawling, or re-run the visualization after a human review session.

### Step 1 — Collect leads from DuckDuckGo

```bash
python3 scripts/run_pipeline.py collect --zip 30350 --category healthcare --max 15
```

Output: `data/raw_leads.json`

New leads are appended; duplicates are skipped automatically.

### Step 2 — Crawl websites (incremental by default)

```bash
python3 scripts/run_pipeline.py crawl
```

On the first run, all leads are crawled. On subsequent runs, leads crawled within the past 7 days are automatically skipped. This makes repeat runs fast.

To force re-crawling all sites regardless of cache:

```bash
python3 scripts/run_pipeline.py crawl --force-crawl
```

To change the staleness window to 3 days:

```bash
python3 scripts/run_pipeline.py crawl --crawl-window 3
```

To add Google Business Profile lookups:

```bash
python3 scripts/run_pipeline.py crawl --gbp
```

To add PageSpeed scores (calls Google's free API, ~400 requests/day):

```bash
python3 scripts/run_pipeline.py crawl --pagespeed
```

To retry blocked sites using a real Chromium browser (requires Playwright — see [Section 12](#12-web-dashboard) for install):

```bash
python3 scripts/run_pipeline.py crawl --playwright
```

Sites returning 403 or DNS failure are retried via headless Chromium. Successfully recovered sites are marked `reachable_via_browser`.

Output: `data/enriched_leads.json`

### Step 3 — Score leads

```bash
python3 scripts/run_pipeline.py score
```

With Ollama LLM reasoning summaries:

```bash
python3 scripts/run_pipeline.py score --ollama
```

Output: `data/scored_leads_full.json`

The scoring step reads `enriched_leads.json` if available, falls back to `raw_leads.json`, then `analyzed_leads.json`. Re-run after crawling to pick up new enrichment data.

### Step 4 — Export to CSV and database

```bash
python3 scripts/run_pipeline.py export
```

Output: `data/scored_leads.csv` (from SQLite if populated, otherwise from JSON)

### Step 5 — Generate charts

```bash
python3 scripts/run_pipeline.py viz
```

Output: `viz/output/*.png` and `viz/output/leads_summary.html`

### Step 6 (optional) — Deduplicate leads manually

Deduplication runs automatically during `collect`, but you can run it manually on the full dataset at any time:

```bash
python3 scripts/run_pipeline.py deduplicate
```

This removes entries where business name similarity > 85% and the first 25 characters of the address match, or where two leads share the exact same website URL.

### Step 7 (optional) — Calibrate ICP weights from human overrides

After accumulating human review decisions, you can let the system suggest adjusted scoring weights:

```bash
python3 scripts/run_pipeline.py calibrate
```

The command reads all leads where a human modified the model's score, attributes the delta to specific signals, and outputs a suggested adjustment to `data/calibrated_weights.json`. To lower the minimum number of overrides required:

```bash
python3 scripts/run_pipeline.py calibrate --min-overrides 5
```

---

## 4. Importing Your Own Lead Lists

If you have a CSV from another source (Google Maps export, manual research, healthcare directories), import it directly instead of running the DuckDuckGo collector.

```bash
python3 scripts/run_pipeline.py import --file path/to/your_leads.csv
```

With defaults for fields not present in the CSV:

```bash
python3 scripts/run_pipeline.py import \
  --file "healthcare_leads_30350 (1).csv" \
  --category healthcare \
  --geo-area "30350"
```

Then run crawl and score as normal:

```bash
python3 scripts/run_pipeline.py crawl
python3 scripts/run_pipeline.py score
```

### Accepted CSV column names

The importer recognizes many common variations. Column names are case-insensitive.

| Field | Recognized Column Names |
|-------|------------------------|
| Business name | Business Name, Name, Company, Company Name |
| Website | Website URL, Website, URL, Site, Web |
| Category | Category, Type, Business Type |
| Address | Full Address, Address, Street, Location |
| ZIP / area | Geo Area, ZIP, Zip Code, City |
| Phone | Phone, Phone Number, Telephone |
| Email | Email, Email Address |

Rows without a business name are skipped. Duplicates (matched by name or website) are skipped automatically.

---

## 5. Human Review Session

The review CLI presents each scored lead for approval, modification, or rejection before results are committed to the database.

### Launch a review session

```bash
python3 apps/human_loop/review_cli.py --input data/scored_leads_full.json
```

### Review controls

| Key | Action | What happens |
|-----|--------|--------------|
| A | Approve | Accepts the model's score; marks lead as human-verified |
| M | Modify | Enter a new score (0-100) and a reason note |
| R | Reject | Sets score to 0; excludes from priority outreach |
| S | Skip | Leaves this lead unreviewed for now |
| Q | Quit | Saves progress; you can resume later |

### Resume a session from where you left off

```bash
python3 apps/human_loop/review_cli.py --input data/scored_leads_full.json --from 12
```

Where `12` is the lead index where you stopped.

### Review only leads not yet reviewed

```bash
python3 apps/human_loop/review_cli.py --pending
```

Reads directly from the database and shows only leads with a score but no human review decision.

### Tips for effective review

- Start with **high-score leads first** (the file is already sorted by score descending)
- Use **M (Modify)** when the model scored too high or low based on local knowledge — for example, if you know a practice is part of a large hospital system despite having an independent-looking website
- Use **R (Reject)** for businesses you know are outside your service territory or already have full digital coverage
- The `final_score` in all exports reflects your override — the original model score is preserved separately

---

## 6. Outreach Cadence Tracking

After reviewing leads, use the cadence CLI to track contact attempts and follow-up schedules.

### See all leads with outreach status

```bash
python3 apps/human_loop/cadence_cli.py list
```

Overdue follow-ups are highlighted in red.

### Log a contact attempt

```bash
# Interactive — prompts for all fields
python3 apps/human_loop/cadence_cli.py log 5

# Non-interactive — specify everything via flags
python3 apps/human_loop/cadence_cli.py log 5 \
  --channel email \
  --response interested \
  --contact-person "Dr. Patel (front desk)" \
  --notes "Called back same day — interested in booking integration" \
  --follow-up 2026-05-02
```

Lead IDs are shown in the `list` command output.

### See overdue follow-ups

```bash
python3 apps/human_loop/cadence_cli.py followups
```

Run this daily before making calls. It shows all leads where you scheduled a follow-up and haven't updated the response.

### Update a response after follow-up

```bash
python3 apps/human_loop/cadence_cli.py update 12 \
  --response scheduled \
  --notes "Intro call booked for May 3 at 2pm"
```

Log entry IDs are shown in the `history` and `followups` commands.

### View full contact history for a lead

```bash
python3 apps/human_loop/cadence_cli.py history 5
```

### Export the cadence log to CSV

```bash
python3 apps/human_loop/cadence_cli.py export
# Output: data/outreach_cadence.csv
```

---

## 7. Expanding to New Geographies

### Single new ZIP code

```bash
python3 scripts/run_pipeline.py collect --zip 30342 --category healthcare
```

New leads are appended to `raw_leads.json`. Duplicates are automatically skipped.

### Multiple specific ZIP codes in one run

```bash
python3 scripts/run_pipeline.py collect \
  --zips "30350,30342,30328,30338,30346" \
  --category healthcare \
  --max 10
```

Each ZIP is searched separately. Cross-ZIP duplicates are deduplicated before saving.

### Radius-based expansion (all ZIPs within N miles)

```bash
# Find and search all ZIPs within 10 miles of 30350
python3 scripts/run_pipeline.py collect --center 30350 --radius 10

# 20-mile radius for a wider territory
python3 scripts/run_pipeline.py collect --center 30350 --radius 20
```

The radius uses the Atlanta metro ZIP centroid data in `config/zcta_centroids.csv`. To extend coverage beyond the pre-loaded ZIPs, add rows to that file:

```csv
zip,city,lat,lon
30045,Lawrenceville,33.943,-83.953
```

Lat/lon coordinates for any US ZIP can be found at `simplemaps.com/data/us-zips` (free tier).

### Targeting a different metro area

1. Download ZIP centroid data for your target metro
2. Add rows to `config/zcta_centroids.csv`
3. Update `config/config.yaml` to set a new `default_zip`
4. Run collect with `--center <new_zip> --radius <miles>`

---

## 8. Updating the ICP Model

The ICP scoring model is defined in `apps/scoring/icp_model.py`. All weights are also mirrored in `config/config.yaml` for reference.

### Change scoring weights without editing code

Edit `config/config.yaml`:

```yaml
scoring:
  weights:
    website_missing: 30       # Increase this if website presence is most critical
    no_booking: 20            # Increase if booking integration is your main service
    weak_seo: 20
    no_social: 10
    independent_practice: 15
    strong_digital_maturity: -20
    poor_performance: 10
    mediocre_performance: 5
    gbp_unclaimed: 10         # New in v1.2.0
    gbp_low_rating: 5
    gbp_no_reviews: 5
```

Note: The config file is currently documentation — the module uses `DEFAULT_WEIGHTS` as its source of truth. To wire config weights into runtime scoring, edit `icp_model.py`:

```python
import yaml
with open(ROOT / "config" / "config.yaml") as f:
    cfg = yaml.safe_load(f)
w = {**DEFAULT_WEIGHTS, **(cfg.get("scoring", {}).get("weights", {}))}
```

### Add a new scoring signal

Example: penalize practices that appear in directories but have no direct website.

1. Add the weight to `DEFAULT_WEIGHTS` in `icp_model.py`:

```python
DEFAULT_WEIGHTS = {
    ...
    "directory_only": 8,   # Only appears in health directories, no direct site
}
```

2. Add the detection logic to `score_lead()`:

```python
is_directory_only = status == "dns_failed" and any(
    d in (lead.get("website") or "")
    for d in ["zocdoc.com", "healthgrades.com", "vitals.com"]
)
if is_directory_only:
    reasoning["directory"] = {"flag": "directory_only", "points": w["directory_only"]}
    raw_score += w["directory_only"]
```

3. Add the matching entry to `config/config.yaml` under `scoring.weights` for documentation.

### Change risk level thresholds

In `icp_model.py`:

```python
RISK_THRESHOLDS = {"high": 70, "medium": 40, "low": 0}
```

Lower the `high` threshold (e.g., to 60) to cast a wider net for priority outreach. Raise it to be more selective.

### Add a new practice type to the independent signal list

In `icp_model.py`:

```python
INDEPENDENT_SIGNALS = [
    "family practice", "family medicine", "chiropractic", "chiropractor",
    "dental", "dentist", "wellness", "physical therapy",
    "acupuncture",        # Add new types here
    "optometry", "optometrist",
    "dermatology",
]
```

### Exclude a chain from scoring as independent

In `icp_model.py`:

```python
CHAIN_SIGNALS = [
    "northside", "wellstar", "emory", "piedmont", "kaiser",
    "cvs", "urgent care", "peachtree immediate",
    "concentra",          # Add new chain signals here
    "american family care",
]
```

Any lead whose business name contains a chain signal is not scored as independent, regardless of category.

---

## 9. Customizing Prompt Templates

Ollama prompt templates live in `config/prompts/`. Each template is a Jinja2 `.j2` file. The active versions are set by `CURRENT_SCORING_TEMPLATE` and `CURRENT_REASONING_TEMPLATE` in `apps/scoring/prompt_engine.py`.

### Current active templates (v1.4.0)

| File | Role | What it produces |
|------|------|-----------------|
| `scoring_v2.j2` | Structured JSON analysis | 5-dimension Healthcare Lead Leak Scan + `lead_leak_dimensions` object |
| `reasoning_v2.j2` | Natural language summary | Outreach-ready 2-3 sentence summary tied to the most critical gap |

### The 5-dimension Lead Leak Scan output (scoring_v2)

When `--ollama` is used, each lead's JSON analysis now includes a `lead_leak_dimensions` block:

```json
{
  "opportunity_summary": "...",
  "top_pain_points": ["...", "..."],
  "recommended_services": ["...", "..."],
  "outreach_angle": "...",
  "lead_leak_dimensions": {
    "speed_mobile":        "pass | needs_work | failing | unknown",
    "intake_booking":      "pass | needs_work | failing | unknown",
    "tracking_visibility": "pass | needs_work | failing | unknown",
    "compliance_trust":    "pass | needs_work | failing | unknown",
    "message_clarity":     "pass | needs_work | failing | unknown"
  },
  "confidence": "high | medium | low"
}
```

Each dimension is assessed from the enrichment signals already in the lead record — no extra API calls needed.

### Roll back to v1 templates

Edit `apps/scoring/prompt_engine.py`:

```python
CURRENT_SCORING_TEMPLATE = "scoring_v1"
CURRENT_REASONING_TEMPLATE = "reasoning_v1"
```

### Create a new template version

Copy any existing template as a starting point:

```bash
cp config/prompts/scoring_v2.j2 config/prompts/scoring_v3.j2
```

Available template variables:

| Variable | Type | Description |
|----------|------|-------------|
| `business_name` | string | Lead's business name |
| `category` | string | Business category |
| `website` | string | Website URL |
| `website_status` | string | reachable / dns_failed / blocked / etc. |
| `booking_present` | bool | Online booking detected |
| `has_seo` | bool | SEO title and description present |
| `social_count` | int | Number of social platforms found |
| `icp_score` | int | 0-100 ICP score |
| `risk_level` | string | high / medium / low |
| `gbp_rating` | float or None | Google star rating |
| `gbp_review_count` | int or None | Number of Google reviews |
| `gbp_unclaimed` | bool | True if GBP appears unclaimed |
| `pagespeed_performance` | int or None | Mobile PageSpeed score 0-100 |

The `prompt_version` logged in the `scores` table reflects which template produced each output, enabling A/B comparison across runs.

### Disable Jinja2 (use inline prompts)

If Jinja2 is not installed, the system falls back automatically to inline f-string prompts based on the v1 format. No configuration change needed.

---

## 9a. Web-Ops Discovery Pipeline (SerpAPI)

A separate keyword-driven discovery script targets businesses by web-ops pain keywords rather than healthcare categories.

### Run the Web-Ops discovery scan

Requires a SerpAPI key in `.env` or `.env-local`:

```bash
SERPAPI_KEY=your_key_here
```

Then:

```bash
cd keywords
python3 keywords.py
```

Output: `keywords/discovery/<date>_disc-leads.csv`

### Keyword tiers

| Tier | Intent | Example |
|------|--------|---------|
| T0 | Vendor switching pain — highest intent | "unhappy with web developer Alpharetta" |
| T1 | Immediate pain — 70-85% conversion probability | "ADA website compliance audit Buckhead" |
| T2 | Strategic ongoing — 50-70% | "mobile website conversion rate Roswell" |
| T3 | Recurring retainer intent — 40-60% | "website monitoring retainer services Decatur" |

T0 leads run first. The summary at the end of each run reports T0 hot-switch lead count separately.

### Output columns (22 total)

The discovery CSV includes standard Google Maps fields, scoring columns, **Web-Ops ICP classification**, and **pre-loaded outreach copy**:

| Column | Description |
|--------|-------------|
| `webops_icp_type` | Vertical: legal, healthcare, financial, ecommerce_retail, real_estate, home_services, hospitality_food, professional_services, education, general |
| `compliance_urgency` | high / medium_high / medium / low — reflects regulatory exposure for that vertical |
| `email_subject` | Ready-to-use cold email subject line |
| `email_opening` | First sentence of cold email body |
| `value_prop` | One-sentence service value statement |
| `cta` | Low-friction call to action |
| `urgency_angle` | Data-backed urgency line for follow-ups |

Replace `[COMPANY]` in the outreach columns with the lead's actual name at send time.

### Adjust active tiers and regions

Edit the constants at the top of `keywords/keywords.py`:

```python
ACTIVE_TIERS   = ["T0", "T1", "T2", "T3"]   # Remove tiers to narrow scope
ACTIVE_REGIONS = ["atl_core", "atl_metro"]    # Add "ga_state" or "se_region" to expand
MAX_SEARCHES_TOTAL = 20                        # Hard cap on SerpAPI calls per run
```

---

## 10. Ongoing / Scheduled Runs

For daily or weekly pipeline runs, you typically only need to re-crawl and re-score — not re-collect.

### Typical weekly cadence

```bash
source .venv/bin/activate

# Re-crawl all sites (skips recently-crawled ones automatically)
python3 scripts/run_pipeline.py crawl

# Re-score with updated enrichment data
python3 scripts/run_pipeline.py score

# Export updated CSV
python3 scripts/run_pipeline.py export

# Regenerate charts
python3 scripts/run_pipeline.py viz
```

### Add new leads weekly from a specific ZIP

```bash
python3 scripts/run_pipeline.py collect --zip 30342 --category dental --max 10
```

Then run crawl → score → export as above.

### Automate with cron

```bash
crontab -e
```

Add a line to run every Monday at 6 AM:

```
0 6 * * 1 cd /home/user/n8n-icp-stack && source .venv/bin/activate && python3 scripts/run_pipeline.py crawl >> data/pipeline.log 2>&1
```

Or use n8n's Cron trigger node to orchestrate the full pipeline with notifications (see `n8n/workflows.json`).

---

## 11. Viewing Results and Exports

### Primary output files

| File | Description | Updated by |
|------|-------------|-----------|
| `data/raw_leads.json` | Raw collected leads | collect / import |
| `data/enriched_leads.json` | Leads with website signals | crawl |
| `data/scored_leads_full.json` | Scored leads with reasoning | score |
| `data/scored_leads.csv` | Human-readable export | export |
| `data/leads.db` | SQLite database | review CLI |
| `data/outreach_cadence.csv` | Outreach log export | cadence export |
| `viz/output/*.png` | Charts | viz |
| `viz/output/leads_summary.html` | HTML leads table | viz |

### Query the database directly

```bash
python3 -c "
import sys
sys.path.insert(0, 'apps/storage')
from db import get_conn, get_all_leads_full
conn = get_conn()
leads = get_all_leads_full(conn)
for l in sorted(leads, key=lambda x: x.get('final_score') or 0, reverse=True)[:10]:
    print(l['business_name'], '|', l['final_score'], '|', l['risk_level'])
conn.close()
"
```

### Filter high-priority leads from the CSV

```bash
python3 -c "
import pandas as pd
df = pd.read_csv('data/scored_leads.csv')
high = df[df['icp_score'] >= 70].sort_values('icp_score', ascending=False)
print(high[['business_name','website','icp_score','risk_level','primary_email','primary_phone']].to_string())
"
```

### Open the HTML summary

```bash
xdg-open viz/output/leads_summary.html
```

---

## 12. Web Dashboard

The read-only web dashboard lets anyone on your local network browse and filter leads without needing terminal access.

### Launch the dashboard

```bash
source .venv/bin/activate
python3 scripts/serve_dashboard.py
```

Then open **http://127.0.0.1:8080** in any browser.

### Dashboard pages

| URL | What it shows |
|-----|---------------|
| `/` | Sortable, filterable lead table with score bars and risk badges |
| `/lead/<id>` | Full lead detail: score breakdown, contact info, GBP signals, outreach history |
| `/charts` | All PNG charts from `viz/output/` |
| `/export` | Download the current `scored_leads.csv` |
| `/api/leads` | JSON API — all leads (for programmatic use) |
| `/api/lead/<id>` | JSON API — single lead detail |

### Options

```bash
# Run on a different port or host
python3 scripts/serve_dashboard.py --port 9090

# Expose to LAN (use your machine's IP in the browser URL)
python3 scripts/serve_dashboard.py --host 0.0.0.0

# Point at a non-default database
python3 scripts/serve_dashboard.py --db /path/to/other/leads.db
```

### Required packages

```bash
pip install fastapi uvicorn jinja2
```

These are already included in `requirements.txt`.

### Install Playwright (for blocked-site retry during crawl)

```bash
pip install playwright
playwright install chromium
```

After installing, use `--playwright` with the crawl step to recover data from sites blocked by anti-bot protection.

---

## 13. Weight Calibration

After you have reviewed and modified scores for several leads, the calibration command analyzes the pattern of your overrides to suggest better default weights.

### Run calibration

```bash
python3 scripts/run_pipeline.py calibrate
```

By default, calibration requires at least 5 human overrides. Adjust:

```bash
python3 scripts/run_pipeline.py calibrate --min-overrides 10
```

### What it outputs

The command prints a before/after comparison table showing which signal weights would change and by how much. Results are saved to:

```
data/calibrated_weights.json
```

### Apply calibrated weights

Calibration **never auto-applies** weights unless `auto_apply: true` is set in `config/config.yaml`. To apply manually, copy the suggested values into the `scoring.weights` section of `config/config.yaml`:

```yaml
scoring:
  weights:
    website_missing: 32       # was 30 — calibrated up
    no_booking: 13            # was 15 — calibrated down
    ...
```

Run `python3 scripts/run_pipeline.py score` after updating weights to re-score all leads with the new model.

### Interpreting the report

- **Calibrated up** — your manual scores were consistently higher than the model's for leads with this signal. The model was under-weighting it.
- **Calibrated down** — you consistently scored these leads lower. The model was over-weighting this signal.
- **No change** — fewer than 3 override samples for this signal; not enough data to adjust.

The original weights are always preserved in `config/config.yaml`. The calibrated file is a suggestion, not an overwrite.

---

## 14. n8n Notifications Setup

The n8n workflow in `n8n/workflows.json` can send Slack messages, sync leads to Google Sheets, and email review requests when high-priority leads are found.

### Import the workflow

1. Open n8n at `http://localhost:5678`
2. Go to **Workflows → Import from File**
3. Select `n8n/workflows.json`

### Configure the Cron trigger

The workflow includes a Cron node set to run nightly at 2:00 AM. To change the schedule, open the **Cron Trigger** node and adjust the expression.

### Enable Slack notifications

1. In n8n, open the **Slack — High Priority** or **Slack — Standard** node
2. Add your Slack Incoming Webhook URL as a credential
3. Update `notifications.slack_webhook_url` in `config/config.yaml`:

```yaml
notifications:
  slack_webhook_url: "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
```

### Enable Google Sheets sync

1. In n8n, open the **Google Sheets Sync** node
2. Connect your Google account via OAuth (n8n built-in credential)
3. Set the target spreadsheet ID in `config/config.yaml`:

```yaml
notifications:
  google_sheet_id: "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms"
```

The sheet must have a header row matching the `scored_leads.csv` column names.

### Enable review request emails

1. In n8n, open the **Review Request Email** node
2. Configure SMTP credentials (Gmail, SendGrid, or any SMTP provider work)
3. Set the reviewer's email address in `config/config.yaml`:

```yaml
notifications:
  reviewer_email: "you@example.com"
```

When new leads with score ≥ 70 are found, a formatted summary is emailed automatically after each pipeline run.

### Manual trigger

The workflow also includes a **Webhook** node for manual runs:

```bash
curl -X POST http://localhost:5678/webhook/icp-trigger
```

---

## 15. Quick Reference — All Commands

```bash
# Setup
source .venv/bin/activate

# Full pipeline
python3 scripts/run_pipeline.py
python3 scripts/run_pipeline.py --ollama --gbp --pagespeed

# Import existing CSV
python3 scripts/run_pipeline.py import --file path/to/leads.csv

# Collect — single ZIP
python3 scripts/run_pipeline.py collect --zip 30350 --category healthcare

# Collect — multiple ZIPs
python3 scripts/run_pipeline.py collect --zips "30350,30342,30328" --category healthcare

# Collect — radius from center ZIP
python3 scripts/run_pipeline.py collect --center 30350 --radius 15

# Crawl — incremental (default)
python3 scripts/run_pipeline.py crawl

# Crawl — force re-crawl all
python3 scripts/run_pipeline.py crawl --force-crawl

# Crawl — with GBP + PageSpeed
python3 scripts/run_pipeline.py crawl --gbp --pagespeed

# Crawl — without contact extraction
python3 scripts/run_pipeline.py crawl --no-contacts

# Crawl — retry blocked sites with Playwright (install playwright first)
python3 scripts/run_pipeline.py crawl --playwright

# Score
python3 scripts/run_pipeline.py score
python3 scripts/run_pipeline.py score --ollama

# Export + visualize
python3 scripts/run_pipeline.py export
python3 scripts/run_pipeline.py viz

# Deduplicate leads
python3 scripts/run_pipeline.py deduplicate

# Calibrate ICP weights from human overrides
python3 scripts/run_pipeline.py calibrate
python3 scripts/run_pipeline.py calibrate --min-overrides 5

# Human review
python3 apps/human_loop/review_cli.py --input data/scored_leads_full.json
python3 apps/human_loop/review_cli.py --pending
python3 apps/human_loop/review_cli.py --input data/scored_leads_full.json --from 12

# Cadence tracker
python3 apps/human_loop/cadence_cli.py list
python3 apps/human_loop/cadence_cli.py log <lead_id>
python3 apps/human_loop/cadence_cli.py log <lead_id> --channel email --response interested --follow-up 2026-05-01
python3 apps/human_loop/cadence_cli.py followups
python3 apps/human_loop/cadence_cli.py history <lead_id>
python3 apps/human_loop/cadence_cli.py update <log_id> --response scheduled
python3 apps/human_loop/cadence_cli.py export

# Web dashboard
python3 scripts/serve_dashboard.py
python3 scripts/serve_dashboard.py --port 9090 --host 0.0.0.0

# n8n manual trigger
curl -X POST http://localhost:5678/webhook/icp-trigger
```

---

*Last updated: April 2026 — v1.4.0*

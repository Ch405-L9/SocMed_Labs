# Changelog

All notable changes to this project are documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).  
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.4.0] - 2026-04-17

### Keyword Discovery Enhancements & Healthcare Lead Leak Scan Templates

#### Added

**T0 Keyword Tier — Pain & Dissatisfaction** (`keywords/keywords.py`)
- `T0_KEYWORDS` — 10 "vendor switching intent" queries sourced from `keywords.atl.north.json` ("web development agency not delivering results [CITY]", "unhappy with web developer [CITY]", "switch seo agency [CITY]", etc.); these signal businesses already in vendor-pain mode and appear first in every execution order
- `T0` added to `KEYWORD_TIERS` and `ACTIVE_TIERS`; pipeline now runs T0 → T1 → T2 → T3
- Summary line in discovery output reports T0 hot-switch lead count separately for quick visibility

**Outreach Templates — Pre-Loaded Cold Email Copy** (`keywords/keywords.py`)
- `OUTREACH_TEMPLATES` — 40 entries, one per keyword across all tiers (T0–T3); each maps `keyword_base` → `{email_subject, email_opening, value_prop, cta, urgency_angle}`
- `_get_outreach()` — case-insensitive lookup with first-token fuzzy fallback; returns empty-string placeholder dict on a miss rather than raising
- `normalize_result()` — now attaches all five outreach fields to every lead record; swap `[COMPANY]` at send time
- CSV output expanded from 15 columns to 22; new columns: `webops_icp_type`, `compliance_urgency`, `email_subject`, `email_opening`, `value_prop`, `cta`, `urgency_angle`

**Web-Ops ICP Classification** (`keywords/keywords.py`)
- `_WEBOPS_ICP_MAP` — 9 verticals with compliance urgency levels: `legal` (high), `healthcare` (high), `financial` (high), `ecommerce_retail` (medium_high), `real_estate` (medium), `home_services` (medium), `hospitality_food` (medium), `professional_services` (medium), `education` (medium); falls back to `("general", "low")`
- `_classify_webops_icp()` — keyword-match function against Google Maps `type` string; returns `(webops_icp_type, compliance_urgency)` tuple
- `normalize_result()` — stamps `webops_icp_type` and `compliance_urgency` on every lead before scoring; enables vertical-based filtering and sorting in the output CSV

**Healthcare Lead Leak Scan Prompt Templates** (`config/prompts/`)
- `scoring_v2.j2` — replaces the generic ICP assessment with a structured **5-dimension Lead Leak Scan** framework: Speed & Mobile Experience, Patient Intake & Booking Funnel, Tracking & Visibility, Compliance & Trust Patterns, Patient Message Clarity; each dimension is assessed from existing enrichment signals; output adds `lead_leak_dimensions` object (`pass | needs_work | failing | unknown` per dimension) alongside all existing JSON fields
- `reasoning_v2.j2` — tightened reasoning prompt with explicit rules: reference the gap by name, frame in patient acquisition or compliance terms, end with a first-contact hook; no filler phrases permitted

#### Changed

- `apps/scoring/prompt_engine.py` — `CURRENT_SCORING_TEMPLATE` promoted from `scoring_v1` to `scoring_v2`; `CURRENT_REASONING_TEMPLATE` promoted from `reasoning_v1` to `reasoning_v2`; all `score --ollama` runs now produce the 5-dimension Lead Leak Scan output; `v1` templates remain on disk for rollback

---

## [1.3.0] - 2026-04-16

### Priority 3 Enhancements — Dashboard, Calibration, Playwright, n8n, Deduplication

#### Added

**Human Override Feedback Loop — Weight Calibration** (`scripts/run_pipeline.py`, `apps/storage/db.py`)
- `step_calibrate()` — queries all human score overrides from SQLite; for each signal that fired in overridden leads, computes average (human_score − model_score) delta; adjusts weights proportionally (capped at ±40% per run); requires configurable minimum override count (default 5)
- `_REASONING_KEY_TO_WEIGHT` — maps reasoning dict keys + flag values to weight names for delta attribution
- `db.get_human_overrides()` — returns all leads where a human override score differs from the model score, joined with scoring reasoning
- `run_pipeline.py calibrate` — new CLI step; prints a formatted adjustment report and writes `data/calibrated_weights.json`; `--min-overrides` flag controls threshold
- `config/config.yaml` — new `calibration` section with `min_overrides` and `auto_apply` settings

**Read-Only Web Dashboard** (`scripts/serve_dashboard.py`, `templates/`)
- `serve_dashboard.py` — FastAPI application serving lead data on localhost:8080; reads directly from `data/leads.db`; includes JSON API endpoints at `/api/leads` and `/api/lead/{id}`
- `templates/base.html` — shared navigation layout with sticky nav bar and responsive CSS (no external CDN dependencies)
- `templates/index.html` — sortable, client-side filterable lead table with risk/status/review-state filters; score bar visualization; stat cards for lead counts by tier; live row count display
- `templates/lead_detail.html` — full lead detail view with ICP score bar, reasoning breakdown table, contact signals, GBP data, PageSpeed score, outreach history from cadence log, and human review decision
- `templates/charts.html` — embedded chart images from `viz/output/`; auto-discovers all PNG files
- `GET /export` — serves `scored_leads.csv` as a file download
- `GET /chart/{filename}` — serves individual chart PNGs
- `requirements.txt` — added `fastapi>=0.110.0` and `uvicorn>=0.29.0`
- `config/config.yaml` — new `dashboard` section with host and port settings

**Playwright Integration for Blocked Sites** (`apps/crawler/fetch.py`)
- `fetch_website()` — new `use_playwright` parameter; after receiving a 403/blocked status, automatically retries with Playwright headless Chromium; sets `website_status = "reachable_via_browser"` on success; stamps `last_crawled` and `content_hash` from the rendered HTML
- `enrich_leads()` — passes `use_playwright` through to `fetch_website()`
- `run_pipeline.py crawl` — new `--playwright` flag enables browser retry on blocked sites
- `requirements.txt` — Playwright remains optional (commented out); install with `pip install playwright && playwright install chromium`

**n8n Workflow Expansion** (`n8n/workflows.json`)
- Replaced single webhook trigger with two parallel entry points: Cron node (nightly at 2:00 AM) and Webhook node (manual on-demand); merged via n8n Merge node
- Added `Read Pipeline Summary` step — runs inline Python after export to compute high/medium/low counts as JSON
- Added `Any High-Priority Leads?` IF node — branches on whether `high > 0`
- Added `Slack: High-Priority Alert` — POST to configurable `SLACK_WEBHOOK_URL`; includes structured Block Kit message with lead counts and review command
- Added `Slack: Standard Completion` — sends simplified message when no high-priority leads found
- Added `Google Sheets: Sync High-Priority` — appends scored lead data to a configurable Google Sheet (requires OAuth credential in n8n); uses `appendOrUpdate` mode
- Added `Email: Review Request` — sends formatted email to `REVIEWER_EMAIL` when high-priority leads exist; includes dashboard launch instructions
- Added `env_vars_required` and `setup_notes` documentation fields to the workflow JSON
- `config/config.yaml` — new `notifications` section with `slack_webhook_url`, `reviewer_email`, `google_sheet_id`

**Lead Deduplication and Merge Logic** (`scripts/run_pipeline.py`)
- `deduplicate_leads()` — removes near-duplicate leads using `difflib.SequenceMatcher` fuzzy name matching (threshold 0.85) combined with 25-character address prefix matching; also deduplicates by exact normalized website URL; returns cleaned list and removed count
- `_similarity()` — wrapper around `SequenceMatcher.ratio()` for clean comparison
- `step_deduplicate()` — standalone `deduplicate` pipeline step; loads `raw_leads.json`, runs deduplication, writes back, prints summary
- Deduplication automatically runs after each `collect` step — no separate invocation needed
- `run_pipeline.py deduplicate` — explicit step for running deduplication on existing data

#### Changed

- `scripts/run_pipeline.py` — `step` choices expanded to include `calibrate` and `deduplicate`
- `scripts/run_pipeline.py` — `step_collect()` now runs deduplication automatically after merging new and existing leads

---

## [1.2.0] - 2026-04-16

### Priority 2 Enhancements — Incremental Crawl, GBP Signals, Multi-ZIP, Prompt Templates

#### Added

**Incremental Crawl with Change Detection** (`apps/crawler/fetch.py`, `apps/storage/schema.sql`, `apps/storage/db.py`)
- `content_hash()` — 16-character sha256 of page HTML; stored per-enrichment record
- `utc_now_iso()` — ISO-8601 UTC timestamp stamped on every successful fetch
- `fetch_website()` — stores `last_crawled` and `content_hash` in enrichment dict on 200 status
- `enrich_leads()` — new parameters: `crawl_cache`, `crawl_window_days` (default 7), `force_crawl`; reads prior `enriched_leads.json` to build the cache automatically; skips leads crawled within window; detects unchanged content by hash comparison and reuses prior enrichment data
- `schema.sql` — added `last_crawled TEXT` and `content_hash TEXT` to enrichment table
- `db.py` — `get_enrichment_cache()` returns cached crawl metadata keyed by website URL; migration adds both columns to existing databases
- `run_pipeline.py` — `step_crawl()` loads `enriched_leads.json` as cache source; `--force-crawl` flag bypasses all cache; `--crawl-window N` configures staleness window in days
- `config/config.yaml` — new `crawler.crawl_window_days` and `crawler.force_crawl` settings

**Google Business Profile Signal Extraction** (`apps/collector/gbp.py`)
- `get_gbp_signals()` — searches DuckDuckGo for business name + ZIP + "google reviews"; parses rating (float 1-5) and review count from search snippets using multi-pattern regex; derives `gbp_verified` (has rating and reviews) and `gbp_unclaimed` (no rating or 0 reviews detected)
- `enrich_leads_gbp()` — applies GBP lookup to a list of enriched leads; merges signals into each lead's `enrichment` dict
- `icp_model.py` — three new scoring weights: `gbp_unclaimed` (+10), `gbp_low_rating` (+5, rating < 3.5), `gbp_no_reviews` (+5, review count = 0); added `gbp` entry to `reasoning` output and `signal_flags`
- `_infer_enrichment_from_analysis()` — returns null GBP defaults for pre-existing data
- `schema.sql` — five new GBP columns on enrichment table: `gbp_rating`, `gbp_review_count`, `gbp_photo_count`, `gbp_verified`, `gbp_unclaimed`
- `db.py` — `upsert_enrichment()` expanded to 27 columns including all GBP fields; migration adds GBP columns to existing databases
- `run_pipeline.py` — `--gbp` flag enables GBP lookup after crawl step; `--gbp-pause` controls DDG request pacing
- `config/config.yaml` — new `gbp` section with `enabled` and `pause_seconds` settings

**Multi-ZIP Batch Mode** (`scripts/run_pipeline.py`)
- `find_zips_within_radius()` — loads `config/zcta_centroids.csv`; computes Haversine distance from a center ZIP to all others; returns sorted list within the specified radius
- `_haversine_miles()` — pure-Python great-circle distance formula; no external dependency
- `_load_zip_centroids()` — parses the centroid CSV; handles missing file gracefully
- `step_collect()` — now accepts a list of ZIP codes; deduplicates across ZIPs by name and website within a single run; tags each lead with its source ZIP in `geo_area`
- `--zips` flag — comma-separated list of ZIP codes (`--zips 30350,30342,30328`)
- `--center` and `--radius` flags — expand collection to all ZIPs within N miles of a center ZIP
- `config/zcta_centroids.csv` — 60-entry reference file of Atlanta metro ZIP codes with lat/lon centroids

**Structured Prompt Templating for Ollama** (`apps/scoring/prompt_engine.py`, `config/prompts/`)
- `config/prompts/scoring_v1.j2` — Jinja2 template for structured JSON scoring prompt; conditionally includes GBP, PageSpeed, and other optional fields when present
- `config/prompts/reasoning_v1.j2` — Jinja2 template for natural-language reasoning summary; injects GBP unclaimed and PageSpeed performance context when available
- `_render_template()` — loads and renders the named template via Jinja2; falls back to inline f-string prompts if Jinja2 is not installed or the template file is missing
- `generate_scoring_analysis()` and `generate_reasoning_summary()` — now accept optional `template` parameter to select a specific version; return `prompt_version` in output dict
- `schema.sql` — added `prompt_version TEXT` to scores table
- `db.py` — `upsert_score()` stores `prompt_version`; migration adds column to existing databases; `_SCORES_V12_COLUMNS` migration constant added
- `requirements.txt` — added `jinja2>=3.1.0`
- `config/config.yaml` — new `ollama.prompt_templates` section with `scoring` and `reasoning` template name settings

#### Changed

- `scripts/run_pipeline.py` — `step_collect()` signature changed from single `zip_code: str` to `zip_codes: list[str]`; all callers updated; ZIP resolution (single / list / radius) unified in `main()`
- `apps/scoring/icp_model.py` — max possible score increases from 90 to 115 with GBP signals enabled; scores remain clamped to 100

---

## [1.0.0] - 2026-04-16

### Initial Release

First complete implementation of the Human-in-the-Loop ICP Lead Generation System.

#### Added

**Project Infrastructure**
- `requirements.txt` with all Python dependencies (requests, beautifulsoup4, trafilatura, pandas, matplotlib, seaborn, pyyaml, lxml)
- `Dockerfile.python` for containerized pipeline execution
- `docker-compose.yml` with n8n, Ollama, and Python services
- `config/config.yaml` as the central configuration file for all pipeline modules
- Virtual environment support via standard `venv`; documented for Ubuntu 24.04+ PEP 668 compliance

**Collector Module** (`apps/collector/`)
- `search.py` — DuckDuckGo HTML search scraper; no API key required; extracts business name, address, website URL, and category from search results
- `sources.py` — Business category query templates, booking signal keywords, social domain mappings, and SEO quality indicators for eight healthcare subcategories

**Crawler Module** (`apps/crawler/`)
- `fetch.py` — HTTP website crawler using `requests` and `trafilatura`; extracts booking presence, SEO metadata, social links, HTTPS status, contact form presence, and page summary text
- `render.py` — Optional Playwright-based renderer for JavaScript-heavy pages; gracefully disabled when Playwright is not installed

**Scoring Module** (`apps/scoring/`)
- `icp_model.py` — Deterministic ICP scoring engine; weighted signal model producing a 0-100 opportunity score, risk classification (high/medium/low), and structured reasoning JSON per lead
- `prompt_engine.py` — Ollama local inference integration; structured JSON analysis via `qwen2.5-coder:7b` and natural language reasoning summaries via `llama3.1:8b`; deterministic fallback for all outputs when Ollama is unavailable

**Human Review Module** (`apps/human_loop/`)
- `review_cli.py` — Full-color interactive terminal review tool; displays lead signals, ICP score, score breakdown, and LLM reasoning per lead; supports approve, modify score, reject, skip, and quit with progress preservation; exports final CSV after session

**Storage Module** (`apps/storage/`)
- `db.py` — SQLite CRUD layer; upsert operations for leads, enrichment, scores, and human reviews; CSV export from `leads_full` view; pending review query
- `schema.sql` — Normalized four-table schema (leads, enrichment, scores, human_reviews) with `leads_full` denormalized view; WAL journal mode

**Pipeline Orchestrator** (`scripts/`)
- `run_pipeline.py` — CLI orchestrator supporting full pipeline execution or individual steps (collect, crawl, score, export, viz); `--ollama` flag for LLM enrichment; `--no-crawl` flag to skip re-crawling; file logging to `data/pipeline.log`

**Visualization Module** (`viz/`)
- `dashboard.py` — Five matplotlib/seaborn charts: score distribution, category breakdown, high-priority leads bar chart, digital presence correlation matrix, and human review summary; HTML leads table with styling; multi-source data loading (CSV, JSON, legacy CSV)

**n8n Workflow**
- `n8n/workflows.json` — Webhook-triggered n8n workflow: Search > Crawl > Ollama scoring > CSV export > completion notification; fully self-contained with no external API dependencies

**Lead Leaks and Web-Optimization Kit**
- `HEALTHCARE_LEADS_REPORT_30350.md` — Full ranked outreach report for 29 unique healthcare leads near ZIP 30350; sequential ordered list with ICP score, contact methods, pain points, and inferred contact details for all leads; customized email drafts with phone scripts for the top 3 leads using the BADGR Lead Leak Scan framework
- `website_optimization_workflow.md` — Appended Section 11: Healthcare Practice Outreach Addendum; HIPAA-aware outreach protocol, healthcare-vs-SMB contact hierarchy, bash audit script for healthcare sites, walk-in print template, and compliance guardrails

**Data**
- `data/raw_leads.json` — Seeded with 30 healthcare provider leads from ZIP 30350
- `data/analyzed_leads.json` — Website enrichment results for all 30 leads
- `data/scored_leads_full.json` — ICP-scored output (30 leads, scores ranging 0-90)
- `data/scored_leads.csv` — Human-reviewable CSV export
- `data/leads.db` — SQLite database with all leads, enrichment, and scores populated

**Documentation**
- `README.md` — Full project documentation including architecture diagram, installation steps, step-by-step run instructions, configuration reference, ICP model explanation, troubleshooting guide
- `CHANGELOG.md` — This file
- `FUTURE_DEV.md` — Enhancement roadmap and architectural recommendations
- `.gitignore` — Repository push preparation; excludes data files, virtual environments, compiled artifacts, and secrets

---

## [1.1.0] - 2026-04-16

### Priority 1 Enhancements — Contact Extraction, PageSpeed, Outreach Cadence, CSV Import

#### Added

**Phone and Email Extraction with MX Verification** (`apps/crawler/fetch.py`)
- `_extract_contacts()` — extracts phone numbers from `tel:` links and visible text using regex; extracts emails from `mailto:` links and visible text
- `verify_mx()` — resolves MX DNS records per email domain via `dnspython`; excludes domains that cannot receive mail; caches per-domain results within a crawl run
- `_EMAIL_BLACKLIST` — filters known CDN, CMS, and framework domains (sentry.io, cloudflare.com, squarespace.com, etc.) before MX verification
- `fetch_website()` — new parameters: `extract_contacts` (default `True`), `use_pagespeed`, `pagespeed_api_key`, `pagespeed_strategy`, `pagespeed_timeout`
- `enrich_leads()` — propagates extracted `primary_phone` and `primary_email` up to the lead dict if not already set from the original source
- `requirements.txt` — added `dnspython>=2.4.0`
- `config/config.yaml` — new `contact_extraction` section with `extract_phones`, `extract_emails`, and `verify_mx` toggles

**PageSpeed / Lighthouse Score Integration** (`apps/crawler/fetch.py`, `apps/scoring/icp_model.py`)
- `get_pagespeed_scores()` — calls Google PageSpeed Insights API v5 (free tier, ~400 requests/day/IP); retrieves mobile performance, SEO, and accessibility scores (0–100); optional API key via `--pagespeed-key`
- `fetch_website()` — calls PageSpeed when `use_pagespeed=True` and site is reachable; scores appended to enrichment dict
- `icp_model.py` — two new scoring weights: `poor_performance` (+10 pts, PageSpeed < 50) and `mediocre_performance` (+5 pts, PageSpeed 50–69)
- `icp_model.py` — `score_lead()` reads `pagespeed_performance` from enrichment; adds structured `reasoning["performance"]` entry
- `_infer_enrichment_from_analysis()` — returns `pagespeed_*: None` for pre-existing data without PageSpeed
- `config/config.yaml` — new `pagespeed` section with `enabled`, `api_key`, `strategy`, and `timeout` settings; disabled by default

**Outreach Cadence Tracker**
- `apps/storage/schema.sql` — new `outreach_log` table: channel, contacted_at, contact_person, notes, response (no_response / interested / not_interested / scheduled / bounced), follow_up_date
- `apps/storage/schema.sql` — new `outreach_summary` view: aggregates contact attempts, last_contacted, next_follow_up, last_response per lead
- `apps/storage/schema.sql` — updated `leads_full` view: added primary_phone, primary_email, mx_verified, pagespeed_performance, pagespeed_seo, pagespeed_accessibility columns
- `apps/storage/db.py` — non-destructive schema migration via `migrate_db()`: adds eight new enrichment columns to existing databases without data loss; recreates updated views
- `apps/storage/db.py` — new functions: `log_outreach()`, `update_outreach_response()`, `get_outreach_history()`, `get_pending_followups()`, `get_outreach_summary()`, `export_cadence_csv()`
- `apps/human_loop/cadence_cli.py` — full-color terminal CLI with six subcommands:
  - `list` — table of all leads with scores, contact attempt count, last contact date, next follow-up, and response status; overdue follow-ups highlighted in red
  - `log <lead_id>` — interactive or flag-driven entry for channel, response, notes, contact person, and follow-up date
  - `followups` — lists all leads where `follow_up_date <= today` and response is still `no_response`; supports `--date YYYY-MM-DD` override
  - `history <lead_id>` — full chronological contact log for one lead with all metadata
  - `update <log_id>` — update response and notes on an existing log entry
  - `export` — writes `data/outreach_cadence.csv` with full join across leads, enrichment, scores, and log

**CSV Import Mode** (`scripts/run_pipeline.py`)
- `step_import()` — new pipeline step; reads any CSV with flexible column naming via `_CSV_COLUMN_MAP`; handles variations such as "Business Name", "Website URL", "Full Address", "Zip Code"; deduplicates against existing `raw_leads.json` by business name and website URL; logs import summary with count of new vs. skipped records
- `run_pipeline.py import` — new CLI step; requires `--file PATH`; optional `--geo-area` and `--category` defaults for records missing those fields

#### Changed

- `apps/storage/db.py` — `upsert_lead()` now performs `UPDATE` on existing records (phone, email, website) rather than silently skipping them
- `apps/storage/db.py` — `upsert_enrichment()` expanded to 20 columns including all new contact and PageSpeed fields
- `scripts/run_pipeline.py` — `step` argument now accepts `import` as a valid choice alongside existing steps

---

## [Unreleased]

See `FUTURE_DEV.md` for full enhancement roadmap.

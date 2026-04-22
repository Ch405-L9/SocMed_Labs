# Future Development Roadmap

**Project:** ICP Lead Generation System  
**Current Version:** 1.3.0  
**Document Status:** Active

> Priority 1 items completed in v1.1.0. Priority 2 items completed in v1.2.0. Priority 3 items completed in v1.3.0.

This document outlines recommended enhancements organized by priority and implementation complexity. Items are independent unless noted.

---

## Priority 1 — High Impact, Low Complexity

These enhancements directly improve output quality and require minimal architectural change.

---

### 1.1 Phone Number and Email Extraction

**Problem:** All leads currently have `phone: Unknown` and `email: null`. Outreach requires manual lookup.

**Solution:** Extend `apps/crawler/fetch.py` to extract phone numbers and email addresses from the lead's website HTML during the crawl step.

```python
# Add to fetch.py: _parse_html()
import re

PHONE_PATTERN = r'\(?\d{3}\)?[\s\-\.]\d{3}[\s\-\.]\d{4}'
EMAIL_PATTERN = r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}'

phones = re.findall(PHONE_PATTERN, html)
emails = re.findall(EMAIL_PATTERN, html)
result['phone'] = phones[0] if phones else None
result['emails'] = list(set(emails))[:3]
```

Add MX record verification before including emails in the export:

```python
import dns.resolver  # dnspython package

def verify_mx(domain: str) -> bool:
    try:
        dns.resolver.resolve(domain, 'MX')
        return True
    except Exception:
        return False
```

**Dependency:** `pip install dnspython`

**Impact:** Eliminates manual contact lookup for every lead; directly populates the outreach CSV.

---

### 1.2 Google PageSpeed / Lighthouse Score Integration

**Problem:** The scoring engine uses binary signals (booking: yes/no, SEO: yes/no). A performance score adds a continuous, quantifiable dimension.

**Solution:** Call the PageSpeed Insights API (free, 25,000 queries/day, no billing required) for each reachable website during the crawl step.

```python
import requests

def get_pagespeed_score(url: str) -> dict:
    endpoint = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
    params = {"url": url, "strategy": "mobile", "category": ["performance", "seo", "accessibility"]}
    try:
        resp = requests.get(endpoint, params=params, timeout=30)
        data = resp.json()
        cats = data.get("lighthouseResult", {}).get("categories", {})
        return {
            "performance": round(cats.get("performance", {}).get("score", 0) * 100),
            "seo": round(cats.get("seo", {}).get("score", 0) * 100),
            "accessibility": round(cats.get("accessibility", {}).get("score", 0) * 100),
        }
    except Exception:
        return {}
```

Add `performance_score`, `seo_score`, and `accessibility_score` to the scoring weights in `icp_model.py`. A performance score below 50 on mobile is a strong ICP signal for healthcare practices.

**Impact:** Quantitative, Google-sourced data replaces heuristic signals. Dramatically strengthens email outreach credibility — you can cite specific numbers.

---

### 1.3 Outreach Cadence Tracker

**Problem:** There is no record of when a lead was contacted, follow-up schedule, or response history.

**Solution:** Add an `outreach_log` table to `schema.sql`:

```sql
CREATE TABLE IF NOT EXISTS outreach_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER REFERENCES leads(id),
    channel TEXT,           -- email / phone / walk-in / linkedin
    contact_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    contact_person TEXT,
    notes TEXT,
    response TEXT,          -- no_response / interested / not_interested / scheduled
    follow_up_date TEXT
);
```

Add a `log_contact` command to `review_cli.py` that fires after approval. Export the cadence log alongside the scored CSV.

**Impact:** Closes the loop between lead identification and actual outreach. Prevents duplicate contact attempts and enables follow-up automation.

---

### 1.4 CSV Import Mode

**Problem:** Leads sourced from external tools (Google Maps exports, manual lists, healthcare directories) cannot enter the pipeline without going through the collector step.

**Solution:** Add a `--import` flag to `run_pipeline.py` that accepts a CSV with standardized columns and inserts directly to `raw_leads.json`, skipping DuckDuckGo search entirely.

```bash
python scripts/run_pipeline.py --import path/to/external_leads.csv --crawl --score
```

Column mapping should be flexible: detect common variants (`Business Name`, `Name`, `Company`) using fuzzy header matching.

**Impact:** Enables the pipeline to score any lead list, regardless of source.

---

## Priority 2 — High Impact, Moderate Complexity

---

### 2.1 Incremental Crawl with Change Detection

**Problem:** Running the crawler re-fetches all websites regardless of when they were last checked. For a growing lead list, this becomes slow and produces redundant data.

**Solution:** Store a `last_crawled` timestamp and a hash of the page content in the `enrichment` table. On subsequent runs, skip leads crawled within a configurable window (e.g., 7 days) unless the page hash has changed.

```python
import hashlib

def content_hash(html: str) -> str:
    return hashlib.sha256(html.encode()).hexdigest()[:16]
```

Add a `--force-crawl` flag to bypass the cache when needed.

**Impact:** Reduces crawl time by 60-80% on repeat runs. Enables daily pipeline runs without redundant network traffic.

---

### 2.2 Google Business Profile Signal Extraction

**Problem:** Many healthcare practices have detailed Google Business Profiles (GBP) with reviews, hours, categories, and photos — but the pipeline only reads their direct websites.

**Solution:** Use the Places API (free tier: $200/month credit, ~1,000 free detailed requests) or scrape GBP data from the publicly available HTML at `https://maps.google.com/?q=<business+name>+<zip>`.

Extract:
- Review count and average rating
- Total photo count
- Verified status (claimed vs. unclaimed)
- Response rate to reviews

A practice with an unclaimed GBP is a strong additional ICP signal — add `gbp_unclaimed: +10` to scoring weights.

**Alternative (no API):** Use `serpapi` self-hosted or `googlemaps-scraper` library for zero-cost GBP extraction.

---

### 2.3 Multi-ZIP Batch Mode

**Problem:** The pipeline targets one ZIP code per run. A sales territory may span 10-20 ZIP codes.

**Solution:** Accept a list of ZIP codes or a radius-based expansion from a center point.

```bash
# Explicit ZIP list
python scripts/run_pipeline.py collect --zips 30350,30342,30328,30338,30097

# Radius expansion (requires ZIP centroid data)
python scripts/run_pipeline.py collect --center 30350 --radius 15
```

Deduplicate leads by website URL across ZIP batches before writing to `raw_leads.json`.

**Dependency:** ZIP centroid CSV (public domain, US Census ZCTA data).

**Impact:** Scales outreach from one neighborhood to an entire metro area in a single run.

---

### 2.4 Structured Prompt Templating for Ollama

**Problem:** The current `prompt_engine.py` uses inline f-string prompts. As prompt quality improves through testing, there is no versioning or A/B comparison mechanism.

**Solution:** Move all prompts to `config/prompts/` as Jinja2 template files. Version each template. Log which prompt version produced each LLM output in the `scores` table.

```
config/
  prompts/
    scoring_v1.j2
    scoring_v2.j2
    reasoning_v1.j2
```

```python
from jinja2 import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader("config/prompts"))
template = env.get_template("scoring_v1.j2")
prompt = template.render(lead=lead, score=score)
```

**Impact:** Enables systematic prompt improvement and quality tracking without modifying source code.

---

## Priority 3 — Strategic Enhancements

---

### 3.1 Human Override Feedback Loop

**Problem:** Human override decisions (modifying or rejecting a model score) are stored but not used to improve future scoring runs.

**Current state:** The model proposes a score, the human corrects it, the correction is stored, and the next run makes the same initial proposal.

**Solution:** After accumulating 50+ human overrides, analyze the delta between model scores and human scores by signal combination. Use this to auto-tune the scoring weights in `config/config.yaml`.

This does not require ML training — it is simple weighted average adjustment:

```python
# For each signal combination where human consistently scored lower:
# weight = weight * (avg_human_score / avg_model_score)
```

Store the original weights alongside adjusted weights so the delta is auditable. Expose a `python scripts/run_pipeline.py calibrate` command.

**Impact:** The system improves its ICP model from operator experience over time without any external data.

---

### 3.2 Web Dashboard (Read-Only)

**Problem:** The review CLI requires terminal access. Non-technical stakeholders (sales team, account managers) cannot view or interact with scored leads.

**Solution:** A lightweight read-only web interface using FastAPI + Jinja2 templates, served locally on port 8080.

```bash
python scripts/serve_dashboard.py
# Opens http://localhost:8080
```

Pages:
- `/` — Sortable, filterable lead table
- `/lead/<id>` — Full lead detail with score breakdown
- `/charts` — Embedded chart images from `viz/output/`
- `/export` — Download current `scored_leads.csv`

The review workflow remains in the CLI for audit trail purposes; the web dashboard is read-only.

**Dependency:** `pip install fastapi uvicorn jinja2`

---

### 3.3 Playwright Integration for Blocked Sites

**Problem:** Fourteen of the thirty leads in the initial dataset returned 403 blocked or DNS-failed statuses. Some of these sites may be reachable by a real browser (anti-bot protection, Cloudflare challenges).

**Solution:** When `fetch.py` receives a 403 status, optionally retry using the Playwright renderer in `render.py`. Gate this behind `config.crawler.use_playwright: true`.

```python
if result["website_status"] == "blocked" and config.crawler.use_playwright:
    from render import render_page
    html = render_page(url, timeout=config.crawler.timeout)
    if html:
        _parse_html(html, result)
        result["website_status"] = "reachable_via_browser"
```

Install Playwright:

```bash
pip install playwright
playwright install chromium
```

**Impact:** Recovers enrichment data for the highest-scoring leads (blocked sites are currently scored with incomplete information).

---

### 3.4 n8n Workflow Expansion

**Current state:** The n8n workflow covers collect > crawl > score > export > notify.

**Recommended additions:**

1. **Scheduled trigger** — Replace the webhook trigger with a Cron node to run the pipeline nightly at 2:00 AM.

2. **Slack / email notification** — After pipeline completion, send a summary (lead count, high-priority count, new leads since last run) to a Slack channel or email address using n8n's built-in nodes.

3. **Google Sheets sync** — Push the scored CSV to a Google Sheet for stakeholder visibility without requiring database access. Use the n8n Google Sheets node (OAuth, free).

4. **Review request routing** — When new high-priority leads (score >= 70) are detected, send a formatted summary to the reviewer's email with a link to launch the CLI review session.

All additions use n8n's built-in node library and require no paid services.

---

### 3.5 Lead Deduplication and Merge Logic

**Problem:** The same business can appear under different names (e.g., "Dunwoody Village Clinic" appears twice in the source data). Duplicate entries waste review time and distort scoring statistics.

**Solution:** Add a deduplication pass at the collection stage using address normalization and fuzzy name matching.

```python
from difflib import SequenceMatcher

def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def deduplicate(leads: list[dict]) -> list[dict]:
    seen = []
    for lead in leads:
        is_dup = any(
            similarity(lead["business_name"], s["business_name"]) > 0.85
            and lead.get("address", "")[:20] == s.get("address", "")[:20]
            for s in seen
        )
        if not is_dup:
            seen.append(lead)
    return seen
```

Add to `run_pipeline.py` collect step before writing `raw_leads.json`.

---

## Technical Debt

These are known limitations in v1.0.0 that should be addressed before significant scale-up.

| Item | Location | Description |
|------|----------|-------------|
| Config not wired to modules | All modules | `config/config.yaml` is defined but modules use inline defaults rather than loading config at runtime. Wire `yaml.safe_load` into each module's initialization. |
| No test suite | All modules | No unit or integration tests exist. Add `pytest` tests for the scoring model (deterministic, easy to test) as a first step. |
| `__init__.py` files missing | `apps/*/` | Module directories lack `__init__.py`. Imports rely on `sys.path` manipulation. Convert to proper Python packages. |
| Logging inconsistency | `scripts/`, `viz/` | Some modules use `print()`, others use `logging`. Standardize on `logging` throughout. |
| Single-file orchestrator | `run_pipeline.py` | The orchestrator is 200+ lines in a single script. Extract step functions into a `pipeline/` package as the number of steps grows. |

---

## Dependency Upgrade Notes

| Package | Current Use | Upgrade Path |
|---------|------------|--------------|
| trafilatura | Text extraction | Pin to `>=1.8.0`; API changed significantly in 1.x vs 0.x |
| matplotlib | Charts | `seaborn-v0_8-*` style names are version-specific; test after upgrades |
| pandas | Data handling | 2.x introduced breaking changes to `DataFrame.append`; already on 2.x |
| beautifulsoup4 | HTML parsing | Stable; no breaking changes expected |

---

*Last updated: April 2026 — v1.0.0 release*

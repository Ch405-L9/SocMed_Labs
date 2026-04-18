<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# BADGR_Phase1_FullOpsManual.pdf

You can absolutely do this yourself *or* hand it to an AI like Claude Code. Below is a ready‑to‑paste Markdown “ops brief” for Claude that:

- Uses your **Phase 1 Full Operations Manual** as a core source.
- Generates 10–15 video scripts.
- Designs 2 ad creatives like the Cursor / Wispr / Stack.Expert examples.
- Builds out the `/social-lab/` folder and slots this manual in.

I’ll first show where this manual fits, then give you the full checklist.

***

## What the Phase‑1 Manual Covers (so we use it correctly)

Your **BADGR Phase 1 Full Operations Manual** defines a 90‑day flagship offer for Atlanta law firms or small medical/dental practices: a 14‑day “Lead Leak \& Compliance Fix” with a strict daily schedule, pre‑flight checklist, per‑client delivery checklist, and RAG/quiz system.[^1]

It includes:

- A locked ICP and offer, plus 90‑day timeline and Gate 0 / Gate 1 criteria (3–5 paying ATL clients, 3+ testimonials, 3+ case summaries, profitable hours × rate).[^1]
- Hour‑by‑hour schedule Monday–Friday (prospect pull, 5 daily personalized emails, delivery block, calls block, build/document, study block, quiz, shutdown ritual).[^1]
- Pre‑flight checklist, failure‑mode diagnostics, operating constitution rules, and detailed scan/fix/proof phases for each client delivery.[^1]

This is perfect raw material for **video scripts** (“day in the life,” “14‑day fix breakdown,” “checklist teardowns”) and for **landing‑page/offer ads** pointing to your Lead Leak \& Compliance Fix.

***

## Where This Manual Belongs in `/social-lab`

When you build the directory we discussed, this PDF should be converted to Markdown and stored in:

```text
/social-lab/
  02_research/
    phase1_ops_manual.md        # cleaned text from BADGR_Phase1_FullOpsManual.pdf
  07_products/
    lead_leak_offer.md          # distilled offer, pricing, benefits, FAQ
```

Claude Code can do the PDF→MD conversion and the splitting.

***

## Paste This for Claude Code: Step‑by‑Step MD Instructions

Below is a Markdown spec you can drop straight into Claude Code or another coding‑capable AI. It tells the model exactly what files to create and how to use your manual + viral patterns.

```markdown
# BADGR Social Lab – Phase 1 Build Instructions (For Claude Code)

Goal: 
Stand up the `/social-lab/` knowledge base for BADGR, generate 10–15 short-form video scripts, and design 2 ad creatives for the “14-Day Lead Leak & Compliance Fix” offer, using existing research + the Phase 1 Full Operations Manual as primary sources.

---

## Phase 0 – Setup & Imports

1. Create a project root folder named `social-lab/`.
2. Inside it, create these subfolders:

   ```text
   /social-lab/
     00_admin/
     01_brand/
     02_research/
     03_prompts/
     04_content_blueprints/
     05_analytics/
     06_distribution/
     07_products/
     08_legal_and_policy/
```

3. Assume the following source documents are available in the environment:
    - `BADGR_Phase1_FullOpsManual.pdf` – Phase 1 Full Operations Manual (14-Day Lead Leak \& Compliance Fix).
    - `Marketing&FULLplatformNarratives.txt` – BADGR business \& marketing compendium.
    - `BADGR_business_information_1.txt` – company profile YAML.
    - `prompt_social-media_lab-results.txt` – viral dev video research \& examples.
    - `viral_formats_2026.md` – 2026 viral format + platform rules.
    - `Market Research & Behavioral Analytics Report_ Str.md` – market research.
    - `atlanta_market.md`, `seo_optimization.md`, tutorials for brand voice and trend scanner.
4. For every transformation below, preserve original files; create *new* cleaned Markdown files in `/social-lab/`.

---

## Phase 1 – Normalize Brand + Offer Docs

### 1.1 Brand Profile

1. Read `BADGR_business_information_1.txt`.
2. Create `/social-lab/01_brand/brand_profile.yaml`:
    - Normalize YAML keys (`company_name`, `legal_name`, `founded`, `naics`, `emails`, `phones`, `addresses`, `social_handles`, `brand_colors`, etc.).
    - Keep only accurate, non-duplicated info; remove any comments that are only for the old system.
3. Validate the YAML is syntactically correct.

### 1.2 Messaging Narratives

1. Read `Marketing&FULLplatformNarratives.txt`.
2. Create `/social-lab/01_brand/messaging_narratives.md` with sections:
    - `## Company Overview`
    - `## Founder Narrative`
    - `## Origin Story`
    - `## Mission`
    - `## Vision`
    - `## Core Values`
    - `## Ethical AI Commitments`
    - `## Service Overviews` (one subsection per major service)
    - `## BADGR Bolt Overview` (keep high-level only; deeper product details will move later)
3. Remove any internal prompts, meta-instructions, or duplicated content; keep this as clean narrative copy.

### 1.3 Phase 1 Offer (Lead Leak \& Compliance Fix)

1. Convert `BADGR_Phase1_FullOpsManual.pdf` to Markdown.
2. From that, create two new files:
    - `/social-lab/02_research/phase1_ops_manual.md`
        - Preserve the structure of the manual: 90-day timeline, daily schedule, pre-flight checklist, gates/failure modes, quiz/RAG setup, per-client checklist, weekly metrics template.
        - Use clear headings and bullet lists; do not change wording.
    - `/social-lab/07_products/lead_leak_offer.md`
        - Distill and rewrite the offer into concise marketing copy:
            - Target ICP (ATL law firms or small medical/dental practices).
            - Promise: 14-Day Lead Leak \& Compliance Fix.
            - Deliverables: before/after performance \& compliance report, fixes applied, legal templates, upsell options.
            - Pricing band (\$197–\$500) and what each tier includes.
            - Process overview in 3–5 steps.
            - FAQ and risk-reversal points (e.g., “no new tools until Gate 1,” auditability, HIPAA-aware workflow).

---

## Phase 2 – Viral Patterns \& Platform Research

### 2.1 Viral Dev Video Research

1. Read `prompt_social-media_lab-results.txt` and both copies if necessary.
2. Create `/social-lab/02_research/viral_dev_videos_2025.md` containing:
    - Summary paragraph of what was researched (25+ viral tech/full-stack videos).
    - Table of key example videos (Roger Chappel, Asif Hassam, etc.) with columns:
        - Creator, Platform, Format, Face/Faceless, Topic, Approx Length, Engagement Notes, Link (if available).
    - Platform summary table:
        - Platform, Typical viral views, Top content type, Primary engagement driver.
    - Bullet list of “Patterns Observed” (hooks, length, faceless vs face, posting cadence, sound choices).
3. Strip out any chain-of-thought or meta commentary; keep only usable facts and tables.

### 2.2 Viral Formats 2026

1. Read `viral_formats_2026.md`.
2. Ensure `/social-lab/02_research/viral_formats_2026.md` is:
    - Clean GFM with:
        - Table of formats + virality scores.
        - Hook formula section.
        - Platform algorithm rules for TikTok, Reels, Shorts, LinkedIn.
        - Trending audio strategy and “when to post” triggers.
3. Add a short intro section noting source summary (e.g., Virvid + HubSpot aggregated research).

### 2.3 Market Context

1. Read `Market Research & Behavioral Analytics Report_ Str.md`, `atlanta_market.md`, `seo_optimization.md`.
2. Create `/social-lab/02_research/market_context_atlanta.md`:
    - Key facts about Atlanta SMB landscape (number of businesses, typical web/AI gaps).
    - Why the 14-Day Lead Leak \& Compliance Fix is compelling in this market.
    - Any relevant stats about web performance, accessibility, and compliance issues for SMBs.

---

## Phase 3 – Video Series \& Script Blueprints (10–15 Videos)

Use:

- `viral_dev_videos_2025.md`
- `viral_formats_2026.md`
- `lead_leak_offer.md`
- `phase1_ops_manual.md`


### 3.1 Define 3–4 Recurring Series

Create `/social-lab/04_content_blueprints/video_series_overview.md` with at least these series:

1. **“Lead Leak Clinic”** – Before/after teardown of anonymous ATL SMB sites.
2. **“Phase 1 Daily Ops”** – Day-in-the-life snippets based on the hourly schedule.
3. **“Compliance Check in 60 Seconds”** – Fast breakdown of one checklist item (HIPAA, ADA, WCAG).
4. **“RAG Lab”** (optional) – How the local RAG / quiz system works for quality control.

For each series specify:

- Primary platforms (TikTok, Reels, Shorts, LinkedIn).
- Face vs faceless.
- Typical length (15–30s or 30–60s).
- Posting cadence (e.g., 1–2 per week per series).
- KPI focus (saves, shares, clicks, or watch time).


### 3.2 Generate 10–15 Concrete Short‑Form Scripts

Create `/social-lab/04_content_blueprints/scripts_shortform.md` with **script templates**, not prose essays.

Each script must include:

- Title (internal working name).
- Intended series (from 3.1).
- Platform(s).
- Hook (0–3 seconds).
- Beat-by-beat structure:
    - Scene A-roll (what’s on camera).
    - Scene B-roll/screen capture.
    - On-screen text overlays.
    - Voiceover or narration bullets.
    - CTA at the end (“Book a free 14-day leak check”, “DM ‘LEAD’ for teardown”, etc.).

Example structure for Script 1 (Claude should follow this pattern for all):

```markdown
### Script 1 – “Your Website is Quietly Failing Intake Forms”

- Series: Lead Leak Clinic
- Platforms: TikTok, Instagram Reels, YouTube Shorts
- Length: ~30 seconds
- Hook (0–3s):
  - On-screen text: “Your intake form might be broken and you have no idea.”
  - VO: “If you’re an Atlanta law firm, this 10-second test could save you clients.”
- Beats:
  1. Show cursor clicking ‘Submit’ on a demo form → nothing happens.
  2. Overlay checklist item from Per-Client Delivery Checklist about manually testing all CTAs.
  3. Quick before/after: error → fixed form with confirmation.
  4. Text overlay: “14-Day Lead Leak & Compliance Fix – Atlanta only.”
- CTA:
  - VO: “Comment ‘CHECK’ and I’ll run this test on your site.”
  - Button/description: link to Lead Leak landing page.
```

Claude should produce **at least 10 scripts** in this format, mixing:

- 4 scripts for “Lead Leak Clinic”.
- 3 scripts for “Phase 1 Daily Ops”.
- 3 scripts for “Compliance Check in 60 Seconds” / “RAG Lab”.

Every script should reference a real element from the manual (e.g., 5 emails/day, pre-flight checklist, CI/CD prompt, quiz/RAG routine).

---

## Phase 4 – Ad Creative Briefs (2 Concepts)

Create `/social-lab/04_content_blueprints/ad_creatives.md` with **two ad briefs** modeled after:

- Cursor demo ad – code editor + live person + simple CTA.
- Wispr Flow / Stack.Expert / Polsia examples – bold text, minimal layout, direct offer.


### 4.1 Ad 1 – “14-Day Lead Leak \& Compliance Fix”

- Objective: Drive click-through to the Lead Leak landing page.
- Format: Vertical video + image variations (for Reels, Shorts, LinkedIn, X).
- Layout:
    - Dark or muted background.
    - Center screen: browser window showing Lighthouse report or CI/CD scan.
    - Small circular webcam or faceless avatar in corner.
- Copy:
    - Headline: “Atlanta law firm? Your website is leaking leads.”
    - Subheadline: “Fix HIPAA \& ADA issues in 14 days without rebuilding your site.”
    - CTA button: “Book a free leak check.”
- Mandatory elements:
    - BADGR logo bug in a corner.
    - 14-Day timeline cue (maybe a progress bar animation).
    - Fine print: “Not legal advice. All templates reviewed by your counsel.”


### 4.2 Ad 2 – “No New Tools. Just Fixed Revenue Leaks.”

- Objective: Retarget warm audiences who saw organic videos.
- Format: Static or motion graphic.
- Layout:
    - Simple black background.
    - Top text, large: “No new platform. No new logins.”
    - Middle text: “One 14-day pass. Your site stops bleeding leads.”
    - Bottom: “BADGR – Atlanta Web Compliance \& Lead Leak Clinic”
    - CTA button: “See how the 14-day fix works.”
- Visuals:
    - Subtle flowchart/boxes in outline behind text, referencing your operations manual timeline.
    - Color palette from BADGR brand (blue, green accent).

For each ad, Claude should output:

- A copy block.
- A layout description (for designer or AI image tool).
- Suggested platform placements and aspect ratios.

---

## Phase 5 – Analytics \& Experiment Log

1. In `/social-lab/05_analytics/`, create:
    - `kpi_definitions.md`:
        - Define views, unique viewers, watch time %, saves, shares, clicks, replies, booked calls, new clients.
        - Map which KPIs matter most by platform (e.g., saves \& shares for Reels/TikTok, CTR for ads).
    - `experiment_log_2026Q2.csv`:
        - Columns: `date, platform, series, script_id, hook_text, video_length_sec, views, watch_time_pct, saves, shares, link_clicks, calls_booked, new_clients, notes`.
2. Initialize `kpi_definitions.md` with target ranges for the first 90 days (conservative, not “viral or bust”).

---

## Phase 6 – Prompt Library

1. Transform existing prompt/tutorial docs into clean prompt files under `/social-lab/03_prompts/`:
    - `tutorial_trend-scanner.txt` → `trend_scanner_prompt.md`
    - `tutorial_brand_voice.txt` → `brand_voice_prompt.md`
    - Any competitive-analysis prompts → `competitive_analysis_prompt.md`
2. Also create `meta_prompt_social_lab.md` using the meta-prompt structure already provided in previous work (phases: research, strategy, execution blueprints, KB \& metrics). Make sure placeholders like `{{brand_name}}` and `{{niche_description}}` are in place.

---

## Output Requirements

- All new files must be valid GitHub-Flavored Markdown or YAML/CSV where specified.
- Keep everything deterministic and structured for easy use by local LLMs.
- Do not invent new offers; stick to the “14-Day Lead Leak \& Compliance Fix” and existing BADGR services.

```

***

If you want, next step can be: you paste this into Claude Code, let it generate the files, then send me whichever outputs you want refined (scripts, ad copy, or folder layout), and I’ll tighten hooks, CTAs, and technical accuracy around the manual and your brand.


<div align="center">⁂</div>

[^1]: BADGR_Phase1_FullOpsManual.pdf```


BADGR Social Lab + Phase 1 Ops – Claude Code Setup
Phase 0 – Project Context
Goal: Combine the Phase 1 Full Operations Manual (14‑day lead leak offer) with a viral short‑form content system and /social‑lab/ knowledge base so BADGR can generate leads and authority in parallel.

Primary offer to promote: “14‑Day Lead Leak & Compliance Fix” for 5–25‑person Atlanta law firms or small medical/dental practices.

Main channels for content: TikTok, Instagram Reels, YouTube Shorts, LinkedIn (optional: X and Facebook Reels).

Claude Code should treat this document as the single source of truth when creating files, scripts, or autom automations for the Social Lab.

Phase 1 – Create the /social-lab/ Folder Tree
Task: Generate this directory layout on disk and stub all .md files with headings only.

text
/social-lab/
  00_admin/
    README.md
    change-log.md
    glossary.md
  01_brand/
    brand_profile.yaml
    messaging_narratives.md
    visual_assets/
      README.md
  02_research/
    viral_dev_videos_2025.md
    platform_benchmarks_2025.md
    viral_formats_2026.md
    market_context_atlanta.md
  03_prompts/
    meta_prompt_social_lab.md
    trend_scanner_prompt.md
    brand_voice_prompt.md
    competitive_analysis_prompt.md
  04_content_blueprints/
    archetypes/
      before_after_website.md
      stack_breakdown_60s.md
      ai_tool_demo_faceless.md
      client_story_pov.md
    scripts/
      short_video_scripts_wave1.md
      ad_script_templates.md
    hooks_and_ctas.md
  05_analytics/
    kpi_definitions.md
    experiment_log_2026Q2.csv
    charts/
      README.md
  06_distribution/
    platform_playbooks/
      tiktok_2026_playbook.md
      instagram_reels_2026_playbook.md
      youtube_shorts_2026_playbook.md
      linkedin_b2b_content.md
    posting_calendar_2026Q2.csv
  07_products/
    badgr_phase1_offer.md
    badgr_bolt_overview.md
    offer_ladders_and_packages.md
  08_legal_and_policy/
    privacy_and_data_use.md
    ai_disclosure_policy.md
    terms_and_disclaimers_snippets.md
Claude instructions:

Create all folders and empty files.

Inside each .md, add an H1 that matches the filename and a one‑sentence TODO line.

Commit this as the initial project baseline if you’re using git.

Phase 2 – Import and Normalize Existing Docs
Goal: Move your current files + PDF content into the new structure in cleaned‑up form.

2.1 Brand and products
Inputs:

BADGR_business_information_1.txt → company profile.

Marketing&FULLplatformNarratives.txt → long narratives + BADGR Bolt info.

Claude steps:

Parse BADGR_business_information_1.txt into YAML and write to 01_brand/brand_profile.yaml:

Company name, legal info, address, contact, social links, brand colors, core services, ICP.

From Marketing&FULLplatformNarratives.txt, split into:

01_brand/messaging_narratives.md – company story, values, AI ethics, positioning.

07_products/badgr_bolt_overview.md – everything specific to BADGR Bolt.

07_products/offer_ladders_and_packages.md – service descriptions + pricing tiers.

Clean wording minimally (typos, duplicated sections) but preserve your voice and examples.

2.2 Research and market context
Inputs:

Viral video research (prompt_social-media_lab-results.txt – both copies).

Viral formats summary (viral_formats_2026.md).

Market + SEO docs (Market Research & Behavioral Analytics Report_ Str.md, atlanta_market.md, seo_optimization.md).

Claude steps:

Merge the two prompt_social-media_lab-results versions into 02_research/viral_dev_videos_2025.md:

Keep: named examples, tables, platform averages, pattern sections.

Remove: meta‑commentary, chain‑of‑thought, duplicate paragraphs.

Copy viral_formats_2026.md into 02_research/viral_formats_2026.md and prepend a short “Sources & Method” paragraph.

Summarize the market/SEO docs into:

02_research/market_context_atlanta.md – Atlanta SMB landscape + pain points.

07_products/offer_ladders_and_packages.md – reference any SEO packages or guarantees.

2.3 Phase 1 Ops manual integration
Input: BADGR_Phase1_FullOpsManual.pdf (14‑day Lead Leak & Compliance Fix).

Claude steps:

Create 07_products/badgr_phase1_offer.md with sections:

Offer summary (ICP, promise, price band, 90‑day gate model).

14‑day delivery checklist (from the manual’s pre‑flight and delivery steps).

90‑day Gates, failure modes, and constitution (Gate 0, Gate 1, 7 rules).

Create 02_research/platform_benchmarks_2025.md and add a section:

“Operational cadence” summarizing the daily schedule (lead gen, delivery, study, RAG) as the baseline for content integration.

Phase 3 – Map Ops Schedule to Content Slots
Goal: Layer content creation onto the existing Phase 1 schedule without breaking the 5‑email, 20‑lead daily rhythm.

Claude steps:

In 06_distribution/posting_calendar_2026Q2.csv, generate a 4‑week calendar with columns: date, day, platform, series, slot, status.

Add 3 content slots per week:

Tue, Thu, Sat at 4:30–5:00 PM (right after quiz / shutdown) for short‑form recording.

Tie each slot to one “series” (see next phase).

Update 02_research/platform_benchmarks_2025.md with a short note:

“Content work happens only in defined slots; no prospecting or delivery time is sacrificed.”

Phase 4 – Define Signature Series and First 12 Scripts
Goal: Turn the research patterns into concrete scripts for your first 10–15 videos.

4.1 Series definitions
In 04_content_blueprints/archetypes/*.md, Claude should describe these four recurring series:

Atlanta Stack Check – before/after law‑firm and clinic websites.

Full‑Stack in the Wild – quick builds / fixes in Cursor or VS Code.

One Prompt, One System – AI automation and RAG flows for solo firms.

Tech Myth Clinic – short myth‑busting clips for non‑technical owners.

Each archetype file should include:

Purpose and ICP.

Best platforms (Reels/Shorts/TikTok/LinkedIn).

Ideal length (20–60 seconds).

Visual style (faceless vs face, screen‑share vs talking‑head).

Required assets (logos, overlays, B‑roll).

4.2 First 12 short‑form scripts
In 04_content_blueprints/scripts/short_video_scripts_wave1.md, Claude should generate 12 full scripts (scene‑by‑scene), three per series:

For each script, include:
Title (internal).

Hook line (0–3s).

Approx length.

Shot list (Scene 1, Scene 2, … with what’s on screen).

Voiceover text or bullet outline.

On‑screen text overlays / captions.

CTA line and button text (“Book a 14‑day leak scan”, etc.).

Suggested breakdown (Claude can flesh out):
Series 1 – Atlanta Stack Check

Script 01 – “Law Firm Site: 8‑Second Load to 1.2s”

Script 02 – “Clinic Homepage: 3 Hidden ADA Risks”

Script 03 – “Before/After: Contact Page That Actually Books Calls”

Series 2 – Full‑Stack in the Wild

Script 04 – “Fixing CLS in 45 Seconds (Live in DevTools)”

Script 05 – “Turn a 5‑Page Site into a 14‑Day Funnel”

Script 06 – “Cursor Session: Generate First Draft of GA‑Friendly Legal Copy”

Series 3 – One Prompt, One System

Script 07 – “One Prompt to Auto‑Tag Every Lead Email”

Script 08 – “Local RAG: Ask Your Own SOPs for Help”

Script 09 – “How a Solo Attorney Ends Daily ‘Website Panic’ with One System”

Series 4 – Tech Myth Clinic

Script 10 – “Myth: ‘HIPAA Means No Online Forms’”

Script 11 – “Myth: ‘Cheap Hosting Is Good Enough’”

Script 12 – “Myth: ‘AI Will Replace My Paralegal’ vs Reality: Assistive Automation”

Claude should tailor language to your existing brand voice (direct, ROI‑focused, low fluff) using tutorial_brand_voice.txt as a reference.

Phase 5 – Ad Creatives Mirroring Cursor / Wispr / Stack.Expert
Goal: Design 1–2 ad concepts that look like your reference screenshots and point to your Phase 1 landing page.

5.1 Ad 1 – “Cursor‑Style Live Fix” (Sign‑up CTA)
File: 04_content_blueprints/scripts/ad_script_templates.md (Section “Ad 1 – Live Fix”).

Claude should define:

Layout:

Dark background.

Center: screen recording of code editor + Lighthouse report (like your Cursor example).

Bottom‑left: small circular webcam of you (optional) or BADGR logo.

Bottom‑right: “Sign up” button.

Copy:

Top headline: “Your Atlanta website is quietly leaking cases.”

Sub‑line: “14‑Day Lead Leak & Compliance Fix. Before/after report, HIPAA‑aware, flat fee.”

CTA: “Book your free 10‑minute leak video.”

Script:

0–3s hook: mid‑sentence start over code: “…and this is why your site never makes it past page one.”

3–20s: show inspection of a real‑world issue; overlays with metrics drops.

20–30s: flip to your landing page + quick CTA explanation.

5.2 Ad 2 – “Polsia‑Style Solopreneur Promise” (Learn‑more CTA)
File: same ad_script_templates.md (Section “Ad 2 – Founder Promise”).

Layout:

Dark background with thin orange/green BADGR accent.

Center text only, simple diagram faint in the background (org chart / funnel).

Copy:

Headline: “No co‑founder. No IT department. No website drama.”

Sub‑quote: “Just you, one prompt, and BADGR handles the rest.”

Tagline: “14‑Day Lead Leak & Compliance Fix for Atlanta law and medical practices.”

CTA button: “See the 14‑day plan”.

Script:

Static visual, 15–20s voiceover summarizing the offer and reassuring about compliance.

Claude can also output Figma‑style text specs (font sizes, colors) if needed.

Phase 6 – KPIs, Experiment Log, and Charts
Goal: Make testing and iteration baked in.

6.1 KPI definitions
In 05_analytics/kpi_definitions.md, Claude should define:

Views per video.

Average watch time and 3‑second hold rate.

Saves and shares per 1,000 views.

Click‑through to landing page.

Discovery vs follower reach.

Booked calls and closed clients traced to content.

6.2 Experiment log
In 05_analytics/experiment_log_2026Q2.csv, Claude should create a header row:

text
date,platform,series,script_id,hook,video_length_sec,views,avg_watch_time_sec,saves,shares,comments,clicks,booked_calls,closed_clients,notes
Every time you publish a new short, add a row manually or via script.

6.3 Charts
Later, Claude (or another code model) can generate and save charts into 05_analytics/charts/, such as:

Videos by platform.

Conversions by series.

Watch‑time vs click‑through.

Use the JSON summary approach from our earlier run as a pattern, but this can wait until you have at least 20 posts.

Phase 7 – Local RAG Integration for Social Lab
You already have instructions in the Phase 1 manual for building a local RAG using Ollama + ChromaDB. Reuse that pattern for the Social Lab knowledge base.

Claude steps:

Mirror the structure under /home/badgr/rag/docs/social_lab/.

Ingest:

All .md files from /social-lab/.

Selected market and ops content from the manual (anonymized).

Create ingestion and query scripts:

social_lab_ingest.py

ask_social_lab.py "question here"

This lets your local models answer “What hook formats worked best last month?” or “Show me the script for Tech Myth Clinic – Script 11” from your own data.

Phase 8 – How You Use This Today
Paste this entire Markdown file into Claude Code as a project brief.

Ask Claude to:

“Generate the /social-lab/ folder structure and stub files exactly as described in Phases 1–2.”

Then: “Fill in short_video_scripts_wave1.md with the 12 scripts defined in Phase 4.2.”

Then: “Fill in ad_script_templates.md with detailed specs for Ad 1 and Ad 2.”

Once those files exist, you record the videos, run the ad tests, and update the experiment log.

*** VIP *** ================================>>> MUST READ BELOW \/

I have plenty of prompt, md, guides, etc., that "MAY" be of use with this make shift local Ollama model RAG setup. Please feel free to peruse if you have the ability to at, '/home/t0n34781/BADGR LLC'. If you cannot view the foldes / files in that DIR, let me know, I'll move them to this Proj DIR

*** VIP *** =======================>>> END

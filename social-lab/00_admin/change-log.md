# change-log

All significant changes to the /social-lab/ knowledge base. Most recent at top.

---

## 2026-04-18 — Stub Fill + Prompt Ware Integration (Claude Code session 2)

**Added:**
- `01_brand/messaging_narratives.md` — full company narrative stack: founder bio, origin story, mission/vision, core values, ethical commitments, 7 positioning angles, grant-ready versions (Hello Alice, NAACP, CDFIs, bank underwriting), brand constants
- `02_research/market_context_atlanta.md` — SMB digital presence stats (40% no website, 70% losing customers, 85/70% first-year survival split), mobile-first data, digital marketing ROI benchmarks, BADGR offer fit analysis, content hook formulas tied to data
- `07_products/badgr_bolt_overview.md` — RSVP/ORP Android app, Open-Core Freemium model, Free/$3.99/$24.99/$49.99 pricing, Phase 1 MVP status, Phase 2 roadmap, tech stack (Kotlin/Jetpack Compose/Firebase/FastAPI), GitHub link
- `03_prompts/sm_business_narratives.md` — grant and funding narrative optimizer
- `03_prompts/sm_copywriter_outreach.md` — B2B law firm cold email generator
- `03_prompts/sm_narrative_architect.md` — evidence-anchored long-form content
- `03_prompts/sm_client_acquisition.md` — B2B prospecting intelligence engine with JSON/CSV output
- `03_prompts/sm_content_enhancement.md` — viral pattern profiler + BADGR funnel generator
- `03_prompts/sm_writing_narrative.md` — prompt engineering iteration strategist
- `03_prompts/sm_visual_analyst.md` — data-to-visual-narrative builder
- Source files committed to project root: Marketing&FULLplatformNarratives.txt, Market Research report, 3 BADGR Bolt files, Social Marketing Prompt Ware/ (7 files)

**Updated:**
- `CLAUDE.md` — reflects completed Phase 7, current chunk count, new source files, updated commands
- `00_admin/README.md` — status table updated, pending stubs noted

**RAG:** re-ingested — 246 chunks (up from 180)

---

## 2026-04-18 — Initial Build (Claude Code session)

**Added:**
- Full `/social-lab/` directory tree (8 folders, 40+ files)
- `01_brand/brand_profile.yaml` — company profile, colors, ICP
- `02_research/viral_dev_videos_2025.md` — 7 named examples, platform table, patterns
- `02_research/platform_benchmarks_2025.md` — corrected 2025 engagement rates, 90-day targets
- `02_research/viral_formats_2026.md` — format table, hook formulas, algorithm rules
- `02_research/phase1_ops_manual.md` — full Phase 1 ops structure
- `04_content_blueprints/scripts/short_video_scripts_wave1.md` — 12 full scene-by-scene scripts
- `04_content_blueprints/scripts/ad_script_templates.md` — Ad 1 + Ad 2 with Figma specs
- `04_content_blueprints/archetypes/` — 4 series defined
- `04_content_blueprints/hooks_and_ctas.md` — hook library + CTA bank
- `05_analytics/kpi_definitions.md` — KPIs, targets, decision rules
- `06_distribution/posting_calendar_2026Q2.csv` — 30 content slots through Jun 27
- `06_distribution/platform_playbooks/` — TikTok, Reels, Shorts, LinkedIn
- `07_products/badgr_phase1_offer.md` — Scan→Fix→Proof, Gate model, pre-flight checklist
- `07_products/offer_ladders_and_packages.md` — full pricing matrix
- `08_legal_and_policy/` — privacy, AI disclosure, disclaimer snippets
- `03_prompts/` — meta prompt, trend scanner, brand voice, competitive analysis, cloud workflow
- `social_lab_ingest.py` + `ask_social_lab.py` — local RAG pipeline (Ollama + ChromaDB)
- `README.md`, `CHEATSHEET.md`, `.gitignore` — project scaffolding
- Git repository initialized; 43 files committed

**RAG status:** 139 chunks indexed, collection `social_lab` active

---

## Template for Future Entries

```
## YYYY-MM-DD — [Brief description]

**Added:**
- file or feature

**Updated:**
- file — what changed and why

**Removed:**
- file — why

**RAG:** re-ingested / not needed
```

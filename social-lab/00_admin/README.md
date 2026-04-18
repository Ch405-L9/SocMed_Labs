# README — BADGR Social Lab Knowledge Base

## What This Is

The `/social-lab/` directory is BADGR Technologies' operational knowledge base for short-form content production, social media distribution, and local RAG integration. It serves as the single source of truth for content strategy, video scripts, analytics, and platform playbooks.

## How to Navigate

| Folder | Contents |
|--------|----------|
| `00_admin/` | This README, change log, glossary |
| `01_brand/` | Company profile YAML, messaging narratives, visual assets |
| `02_research/` | Viral video research, platform benchmarks, Atlanta market context, Phase 1 ops manual |
| `03_prompts/` | Reusable Claude/Ollama prompt templates |
| `04_content_blueprints/` | 4 video series archetypes, 12 Wave 1 scripts, ad creative briefs, hooks & CTAs |
| `05_analytics/` | KPI definitions, experiment log CSV, charts |
| `06_distribution/` | Q2 2026 posting calendar, per-platform playbooks |
| `07_products/` | Phase 1 offer, offer ladder, BADGR Bolt overview |
| `08_legal_and_policy/` | Privacy, AI disclosure, disclaimer snippets |

## How This Feeds the RAG

All `.md` files here are designed to be ingested by `social_lab_ingest.py` (Phase 7) into ChromaDB for local query via `ask_social_lab.py`. Keep files clean Markdown — no raw HTML, no footnote URLs, no chain-of-thought.

## Current Status

- Phase 1 (folder structure): ✅ Complete
- Phase 2 (brand, research, products): ✅ Complete
- Phase 3 (posting calendar): ✅ Complete
- Phase 4 (scripts, archetypes, ad creatives): ✅ Complete
- Phase 5 (ad creatives): ✅ Complete
- Phase 6 (KPIs, experiment log): ✅ Complete
- Phase 7 (RAG ingestion scripts): Pending
- Phase 8 (live recording + posting): Pending — begin Tue Apr 21, 2026

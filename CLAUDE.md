# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**BADGR Social Lab** — a content system and social media knowledge base for BADGR Technologies LLC (Atlanta, GA). The goal is to build a viral short-form content pipeline and local RAG knowledge base to support the company's flagship "14-Day Lead Leak & Compliance Fix" offer targeting Atlanta law firms and medical/dental practices.

## Key Source Files

| File | Purpose |
|------|---------|
| `Claude_README.md` | Master project brief — defines all 8 phases and the /social-lab/ folder structure |
| `BADGR_Phase1_FullOpsManual.pdf.md` | Source-of-truth operations manual; daily rhythm, scripts, deliverables |
| `Claude_For_Reference-&-Use-if-Needed/BADGR_business_information_1.txt` | Company profile, brand colors, legal info (YAML-formatted) |
| `Claude_For_Reference-&-Use-if-Needed/badgr_mcp_server.py` | FastAPI MCP server (6 tools: trend_check, brand_voice, competitive_analysis, etc.) |
| `Claude_For_Reference-&-Use-if-Needed/BADGR Phase 1 Service Tiers...md` | Pricing, ICP, packages, SOP prompts |
| `Marketing&FULLplatformNarratives.txt` | Full company narratives, founder bio, service descriptions, grant-ready copy, BADGR Bolt marketing |
| `Market Research & Behavioral Analytics Report_ Str.md` | SMB digital presence stats, ROI benchmarks, AI productivity data |
| `BADGR_Bolt_Final_Report.md` | BADGR Bolt strategic analysis, Open-Core Freemium decision, Phase 2 plan |
| `BADGR Bolt Pricing And Readme.md` | Pricing tiers, competitive landscape, GitHub README draft |
| `Social Marketing Prompt Ware/` | 7 specialized prompts: outreach, narrative, client acquisition, visual analytics |

## Architecture

The project is a **documentation-first knowledge base** — no traditional app framework. Output is a `/social-lab/` directory tree of YAML/Markdown files, later ingested into a local RAG (Ollama + ChromaDB).

### /social-lab/ Structure (fully built)

```
00_admin/       – README (status table), change-log.md, glossary.md
01_brand/       – brand_profile.yaml, messaging_narratives.md, visual_assets/README.md
02_research/    – viral_formats_2026.md, platform_benchmarks_2025.md,
                  viral_dev_videos_2025.md, market_context_atlanta.md, phase1_ops_manual.md
03_prompts/     – meta_prompt_social_lab.md, trend_scanner_prompt.md, brand_voice_prompt.md,
                  competitive_analysis_prompt.md, cloud_research_workflow.md
                  + 7 sm_* prompts (outreach, narratives, acquisition, visual, content, writing)
04_content_blueprints/ – archetypes/ (4 series), scripts/ (12 Wave 1 scripts, 2 ad creatives),
                         hooks_and_ctas.md
05_analytics/   – kpi_definitions.md, experiment_log.csv, charts/README.md
06_distribution/ – posting_calendar_2026Q2.csv,
                   platform_playbooks/ (TikTok, Reels, YouTube Shorts, LinkedIn)
07_products/    – badgr_phase1_offer.md, offer_ladders_and_packages.md, badgr_bolt_overview.md
08_legal_and_policy/ – privacy_and_data_use.md, ai_disclosure_policy.md,
                        terms_and_disclaimers_snippets.md
```

### MCP Server (badgr_mcp_server.py)
- **Runtime**: FastAPI + Uvicorn on `localhost:8765`
- **Tools**: `trend_check` (pytrends), `brand_voice`, `competitive_analysis`, `content_brief`, `platform_optimizer`, `rag_query`
- **RAG backend**: Ollama (local LLM) + ChromaDB (vector store) + sentence-transformers

### RAG Pipeline (Phase 7 — active)
- **Collection:** `social_lab` in `.chroma_db/` — **246 chunks** as of 2026-04-18
- **Embeddings:** `all-MiniLM-L6-v2` via ChromaDB DefaultEmbeddingFunction (ONNX)
- **Generation:** Ollama on `localhost:11434`; default model `phi3:mini`; fallback `llama3.2:3b`
- **Python env:** Always use `.venv/` — system Python has a broken pydantic stub

## Commands

### Daily startup
```bash
source .venv/bin/activate
ollama serve &   # skip if already running
```

### RAG queries
```bash
# Ask a question
.venv/bin/python ask_social_lab.py "what are the LinkedIn algorithm rules for 2026?"

# Show source chunks
.venv/bin/python ask_social_lab.py "HIPAA web compliance" --sources

# Use a different model
.venv/bin/python ask_social_lab.py "hook formulas" --model phi3:mini
```

### Re-ingest after adding files
```bash
.venv/bin/python social_lab_ingest.py
```

### MCP Server
```bash
pip install fastapi uvicorn chromadb sentence-transformers pytrends
python3 Claude_For_Reference-&-Use-if-Needed/badgr_mcp_server.py
pkill -f badgr_mcp_server.py
```

## Content Strategy Snapshot

- **Posting cadence**: 3–5 videos/week, Tue/Thu/Sat at 4:30–5:00 PM
- **Platforms**: TikTok, Instagram Reels, YouTube Shorts, LinkedIn
- **Format**: 15–60 sec faceless screen-share, electronic music, 3-sec hook
- **4 Series**: Lead Leak Clinic · Phase 1 Daily Ops · Compliance Check in 60s · RAG Lab

## Brand Constants
- **Colors**: Deep Blue `#02068D`, Logo Primary `#0E305F`, Accent `#7FA1D3`
- **Tone**: Direct, ROI-focused, authority-driven — no fluff
- **ICP**: Atlanta SMBs — law firms, medical/dental practices (5–25 FTEs)
- **Flagship price band**: $3,000–$5,000 one-time; $650–$3,250/mo retainer

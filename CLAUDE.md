# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**BADGR Social Lab** — a content system and social media knowledge base for BADGR Technologies LLC (Atlanta, GA). The goal is to build a viral short-form content pipeline and local RAG knowledge base to support the company's flagship "14-Day Lead Leak & Compliance Fix" offer targeting Atlanta law firms and medical/dental practices.

## Key Source Files

| File | Purpose |
|------|---------|
| `Claude_README.md` | Master project brief — defines all 8 phases and the /social-lab/ folder structure to build |
| `BADGR_Phase1_FullOpsManual.pdf.md` | Source-of-truth operations manual; daily rhythm, scripts, deliverables |
| `Claude_For_Reference-&-Use-if-Needed/BADGR_business_information_1.txt` | Company profile, brand colors, legal info (YAML-formatted) |
| `Claude_For_Reference-&-Use-if-Needed/badgr_mcp_server.py` | FastAPI MCP server (6 tools: trend_check, brand_voice, competitive_analysis, etc.) |
| `Claude_For_Reference-&-Use-if-Needed/BADGR Phase 1 Service Tiers...md` | Pricing, ICP, packages, SOP prompts |

## Architecture

The project is a **documentation-first knowledge base** — no traditional app framework. Output is a `/social-lab/` directory tree of YAML/Markdown files, later ingested into a local RAG (Ollama + ChromaDB).

### Planned /social-lab/ Structure
```
00_admin/       – README, change log, glossary
01_brand/       – brand_profile.yaml, messaging, visual assets
02_research/    – viral video research, platform benchmarks, market context
03_prompts/     – reusable Claude/Ollama prompts and templates
04_content_blueprints/ – 4 video series, 12 scripts, 2 ad creatives
05_analytics/   – KPI definitions, experiment_log CSV
06_distribution/ – posting calendar, per-platform playbooks
07_products/    – offer sheets, pricing, BADGR Bolt overview
08_legal_and_policy/ – privacy, AI disclosure, disclaimers
```

### MCP Server (badgr_mcp_server.py)
- **Runtime**: FastAPI + Uvicorn on `localhost:8765`
- **Tools**: `trend_check` (pytrends), `brand_voice`, `competitive_analysis`, `content_brief`, `platform_optimizer`, `rag_query`
- **RAG backend**: Ollama (local LLM) + ChromaDB (vector store) + sentence-transformers

## Commands

### MCP Server
```bash
# Install dependencies
pip install fastapi uvicorn chromadb sentence-transformers pytrends

# Run server
python3 Claude_For_Reference-&-Use-if-Needed/badgr_mcp_server.py

# Test endpoints
curl http://localhost:8765/tools
curl -X POST http://localhost:8765/tool/trend_check \
     -H "Content-Type: application/json" \
     -d '{"keyword": "AI for small business Atlanta"}'

# Stop server
pkill -f badgr_mcp_server.py
```

### Future RAG Scripts (to be created in Phase 7)
```bash
python3 social_lab_ingest.py        # Ingest /social-lab/ MD files into ChromaDB
python3 ask_social_lab.py "query"   # Query the RAG
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

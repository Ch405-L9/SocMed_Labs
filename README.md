# BADGR Social Lab

Short-form content system and AI knowledge base for **BADGR Technologies LLC** — technical SEO and website compliance for Atlanta law firms and medical/dental practices.

## What This Is

A fully structured, locally queryable knowledge base that powers:
- 12 ready-to-record video scripts across 4 content series
- 2 ad creative briefs (Cursor-style + Solopreneur Promise)
- Local RAG (Ollama + ChromaDB) — query your own docs in seconds
- Q2 2026 posting calendar (30 slots, Tue/Thu/Sat 4:30 PM)
- Offer docs, pricing, compliance disclaimers, and prompt templates

## Quick Start

```bash
# 1. Activate the environment
source .venv/bin/activate

# 2. Query the knowledge base
python3 ask_social_lab.py "What's the pre-flight checklist for a medical client?"
python3 ask_social_lab.py "Give me a hook for the compliance check series"
python3 ask_social_lab.py "What are the Gate 1 criteria?"

# 3. After editing any file in social-lab/, re-ingest
python3 social_lab_ingest.py
```

**See `CHEATSHEET.md` for the full command reference.**

## Structure

```
SocMed_Labs/
├── social-lab/              # The knowledge base
│   ├── 00_admin/            # README, change log, glossary
│   ├── 01_brand/            # Brand profile YAML, messaging
│   ├── 02_research/         # Viral research, benchmarks, ops manual
│   ├── 03_prompts/          # Reusable Claude/Ollama prompt templates
│   ├── 04_content_blueprints/ # 12 scripts, 4 archetypes, ad creatives
│   ├── 05_analytics/        # KPI definitions, experiment log CSV
│   ├── 06_distribution/     # Posting calendar, platform playbooks
│   ├── 07_products/         # Phase 1 offer, pricing ladder, Bolt
│   └── 08_legal_and_policy/ # Privacy, AI disclosure, disclaimers
├── social_lab_ingest.py     # Index social-lab/ into ChromaDB
├── ask_social_lab.py        # Query the RAG
├── CHEATSHEET.md            # All commands in one place
├── CLAUDE.md                # Claude Code context file
└── requirements.txt         # Python dependencies
```

## Flagship Offer

**14-Day Lead Leak & Compliance Fix** — $3,000–$5,000 flat fee
- Target: Atlanta law firms and small medical/dental practices (5–25 FTEs)
- Scope: Scan → Fix → Proof on existing website (top 5–10 revenue-killing issues)
- Deliverables: Before/after Lighthouse reports, fix log, compliance report, 3 next-step options

## Content Series

| Series | Platform | Length | Style |
|--------|----------|--------|-------|
| Atlanta Stack Check | TikTok, Reels, Shorts | 25–40s | Faceless screen-share |
| Phase 1 Daily Ops | YouTube Shorts, TikTok | 30–50s | Screen-share / DevTools |
| Compliance Check in 60s | TikTok, Reels, LinkedIn | 30–60s | Faceless, text-heavy |
| RAG Lab | YouTube Shorts, LinkedIn | 40–60s | Terminal + Python output |

## Local RAG Stack

- **Embeddings:** `all-MiniLM-L6-v2` via ChromaDB (runs on CPU, fast)
- **Generation:** Ollama — use `phi3:mini` (2.2GB, fits in 4GB VRAM) for speed
- **Storage:** `.chroma_db/` (local, not committed to git)

Pull faster models when ready:
```bash
ollama pull phi3:mini
ollama pull llama3.2:3b
```

# BADGR Social Lab — Cheat Sheet

Everything you need to run this system day-to-day. One page.

---

## Daily Startup

```bash
cd /home/t0n34781/SocMed_Labs
source .venv/bin/activate
```

---

## RAG — Query the Knowledge Base

```bash
# Basic query
python3 ask_social_lab.py "your question here"

# Show which source files were used
python3 ask_social_lab.py "your question" --sources

# Use a faster/smaller model (once pulled)
python3 ask_social_lab.py "your question" --model phi3:mini
python3 ask_social_lab.py "your question" --model llama3.2:3b

# Get more context (default is 5 chunks)
python3 ask_social_lab.py "your question" --top-k 8
```

**Useful queries to save:**
```bash
python3 ask_social_lab.py "What's the pre-flight checklist for a medical client?"
python3 ask_social_lab.py "Give me hook lines for the Atlanta Stack Check series"
python3 ask_social_lab.py "What are the Gate 1 criteria?"
python3 ask_social_lab.py "What's the posting schedule for Q2 2026?"
python3 ask_social_lab.py "What KPIs should I track on TikTok?"
python3 ask_social_lab.py "What's the pricing for the Growth Engine retainer?"
python3 ask_social_lab.py "Give me CTA options that drive comments"
```

---

## RAG — Update the Knowledge Base

Run this any time you add, edit, or delete a file in `social-lab/`:

```bash
python3 social_lab_ingest.py
```

Full wipe and rebuild (if something seems off):
```bash
python3 social_lab_ingest.py --reset
```

---

## Content Workflow

```
Record (Tue/Thu/Sat 4:30 PM)
  → Edit with Submagic (captions/zooms)
  → Post to TikTok + Reels first, Shorts next day
  → Add row to social-lab/05_analytics/experiment_log_2026Q2.csv
  → Re-ingest if you added notes to KB
```

**Experiment log columns:**
`date, platform, series, script_id, hook_text, video_length_sec, views, watch_time_pct, saves, shares, link_clicks, calls_booked, new_clients, notes`

---

## Adding New Research (Cloud → KB Pipeline)

1. Run a prompt from `social-lab/03_prompts/` in Claude.ai, Gemini, or Perplexity
2. Copy the clean output (no chain-of-thought, no footnote URLs)
3. Save to `social-lab/02_research/[topic]_[YYYY-MM].md`
4. Run `python3 social_lab_ingest.py`

---

## Git — Save Your Work

```bash
# Check what changed
git status
git diff

# Save a checkpoint
git add social-lab/ social_lab_ingest.py ask_social_lab.py
git commit -m "brief description of what changed"

# View history
git log --oneline
```

---

## Ollama — Model Management

```bash
# Check what's running
ollama ps

# List installed models
ollama list

# Pull faster models for KB queries
ollama pull phi3:mini        # 2.2GB — fits in 4GB VRAM, use for quick queries
ollama pull llama3.2:3b      # 2.0GB — also fast

# Start Ollama if it stops
ollama serve
```

**Model guide for this machine (RX 6500 XT, 4GB VRAM):**

| Model | Size | Speed | Best For |
|-------|------|-------|---------|
| `phi3:mini` | 2.2GB | Fast (GPU) | Quick KB lookups |
| `llama3.2:3b` | 2.0GB | Fast (GPU) | Quick KB lookups |
| `gemma2:2b` | 1.6GB | Fastest | Simple queries |
| `qwen2.5-coder:7b` | 4.7GB | Slow (CPU) | Complex reasoning |

---

## File Locations — Quick Reference

| What | Where |
|------|-------|
| Video scripts (Wave 1) | `social-lab/04_content_blueprints/scripts/short_video_scripts_wave1.md` |
| Hook library | `social-lab/04_content_blueprints/hooks_and_ctas.md` |
| Ad creative briefs | `social-lab/04_content_blueprints/scripts/ad_script_templates.md` |
| Posting calendar | `social-lab/06_distribution/posting_calendar_2026Q2.csv` |
| Experiment log | `social-lab/05_analytics/experiment_log_2026Q2.csv` |
| KPI definitions | `social-lab/05_analytics/kpi_definitions.md` |
| Phase 1 offer doc | `social-lab/07_products/badgr_phase1_offer.md` |
| Pricing ladder | `social-lab/07_products/offer_ladders_and_packages.md` |
| Brand profile | `social-lab/01_brand/brand_profile.yaml` |
| Prompt templates | `social-lab/03_prompts/` |
| Disclaimer copy | `social-lab/08_legal_and_policy/terms_and_disclaimers_snippets.md` |

---

## Decision Rules (When to Do What)

| Situation | Action |
|-----------|--------|
| Added/edited a KB file | `python3 social_lab_ingest.py` |
| Query returns wrong answer | `--sources` flag to see what it's reading; fix the source file |
| Need trending hooks | Run `trend_scanner_prompt.md` in Perplexity → save to `02_research/` → re-ingest |
| Video flopped | Add row to experiment log; check if 3-sec hold rate was under 40% |
| Video hit | Check save/share rate; if >3%, schedule 2 more in that series |
| Finished Gate 1 | Update `00_admin/change-log.md`; start Phase 2 planning |

# cloud_research_workflow

How to use cloud AI models (Claude.ai, Gemini, Perplexity) to research and update the BADGR knowledge base — without API costs, without data leaving your control, and without building complex pipelines.

---

## The Workflow (3 Steps)

### Step 1 — Run a cloud research session

Open Claude.ai, Gemini Advanced, or Perplexity. Use one of the prompt templates in `03_prompts/`. Paste the prompt, let the model do the heavy lifting.

**Best tool by task:**

| Task | Best Tool | Why |
|------|-----------|-----|
| Competitive research, market data | Perplexity | Web search + citations built in |
| Script writing, brand voice copy | Claude.ai | Best for nuanced tone matching |
| Platform algorithm updates | Perplexity or Gemini | Current web access |
| Long document summarization | Claude.ai | Longest context window |
| Trend scanning | Perplexity | Real-time search |

### Step 2 — Save the output as a clean Markdown file

Copy the response. Open a terminal:

```bash
nano /home/t0n34781/SocMed_Labs/social-lab/02_research/[topic]_[YYYY-MM].md
```

Paste, clean it up (remove chain-of-thought, meta-commentary, footnote URLs). Save.

**File naming convention:**
- `competitive_analysis_atlanta_2026-04.md`
- `hipaa_enforcement_update_2026-05.md`
- `google_cwv_update_2026-Q2.md`
- `tiktok_algorithm_notes_2026-04.md`

### Step 3 — Re-ingest into the knowledge base

```bash
cd /home/t0n34781/SocMed_Labs
python3 social_lab_ingest.py
```

Done. Your local RAG now knows about the new research. Query it:

```bash
python3 ask_social_lab.py "What are the latest HIPAA web enforcement actions?"
```

---

## Research Schedule (Weekly)

| Day | Task | Prompt to use |
|-----|------|--------------|
| Monday AM | Trend scan | `trend_scanner_prompt.md` |
| Monthly | Competitive refresh | `competitive_analysis_prompt.md` |
| When algorithm updates drop | Platform notes | Save to `06_distribution/platform_playbooks/` |
| After each client engagement | Case notes | Save anonymized to `02_research/` |

---

## What Goes Into the KB vs. What Stays in the Cloud

| Keep in KB (local) | Keep in cloud session only |
|-------------------|--------------------------|
| Cleaned research summaries | Raw chain-of-thought outputs |
| Script drafts (reviewed) | Unreviewed first drafts |
| Platform benchmarks (verified) | Speculative claims without sources |
| Anonymized case notes | Anything with client PII |
| Prompt templates | One-off session prompts |

---

## Tips

- **One topic per file.** Don't paste a 10-topic research dump into one file — it hurts retrieval quality.
- **Source at the top.** Add a 1-line "Source: [tool] research session, [date]" at the top of each file.
- **Re-ingest is cheap.** It takes ~30 seconds. Run it any time you add or edit a file.
- **Tag your files by date.** Stale info in the KB is worse than no info — you'll know to refresh files with older dates.

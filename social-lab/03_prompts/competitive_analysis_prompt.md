# competitive_analysis_prompt

Prompt for running competitive analysis on ATL agencies. Paste into Claude.ai, Gemini, or Perplexity. Save the output as a new file in `02_research/` before closing the session.

---

## Prompt

```
You are a market research analyst. I need a competitive analysis for a small tech services company in Atlanta, GA.

COMPANY: BADGR Technologies LLC
OFFER: "14-Day Lead Leak & Compliance Fix" — technical SEO, ADA/WCAG, HIPAA web presence review, and UX fixes for small law firms and medical/dental practices (5–25 FTEs). Flat fee $3,000–$5,000.

RESEARCH TASK
1. Identify 5–8 Atlanta-area agencies or consultants offering similar services (technical SEO, website compliance, web optimization for legal/healthcare SMBs).
2. For each competitor, note:
   - Company name and URL
   - Pricing (if public) or price signals
   - ICP (who they target)
   - Differentiator or positioning angle
   - Weakness or gap BADGR could exploit
3. Identify any Atlanta-specific market trends in legal/medical website compliance that are active right now (ADA lawsuits, Google algorithm updates, HIPAA enforcement news).
4. Output a "positioning gap" summary: what is BADGR uniquely positioned to own that no competitor currently occupies?

OUTPUT FORMAT
- Use clean Markdown with H2 sections and tables where appropriate
- Cite sources (agency website URLs or news outlets)
- Keep it factual — no hype, no filler
- End with a 3-bullet "BADGR Positioning Opportunities" section
```

---

## After Running This Prompt

Save the output to:
```
/social-lab/02_research/competitive_analysis_atlanta_[YYYY-MM].md
```

Then re-ingest:
```bash
python3 social_lab_ingest.py
```

The RAG will now be able to answer questions like "Who are our main competitors?" and "What's our positioning edge?" from local context.

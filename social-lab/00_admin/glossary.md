# glossary

Key terms used across the BADGR Social Lab knowledge base.

---

## Business Terms

| Term | Definition |
|------|-----------|
| **ICP** | Ideal Customer Profile — Phase 1: Atlanta law firms and small medical/dental practices, 5–25 FTEs, owner-led |
| **Gate 0** | Start state — one ICP, one offer, no new tools until Gate 1 criteria are met |
| **Gate 1** | Exit criteria — 3–5 paying clients, 3+ testimonials, 3+ case summaries, profitable hours × rate |
| **Lead Leak** | Revenue lost due to broken forms, slow pages, compliance gaps, or weak CTAs on an existing website |
| **Compliance Fix** | BADGR's process for documenting and correcting HIPAA web presence and ADA/WCAG issues |
| **14-Day Fix** | BADGR's flagship offer — Scan (Days 1–3), Fix (Days 4–10), Proof (Days 11–14) |
| **CICD Verification Prompt** | BADGR's internal prompt that checks SEO meta, Core Web Vitals flags, CTA clarity, and compliance pages |
| **Operating Constitution** | 7 rules that govern how BADGR operates during Phase 1 — see `07_products/badgr_phase1_offer.md` |
| **90-Day Sprint** | The Phase 1 operating window — one ICP, one vertical, one offer, until Gate 1 is reached |

---

## Technical Terms

| Term | Definition |
|------|-----------|
| **RAG** | Retrieval-Augmented Generation — query a local knowledge base with a language model; answers come from your own docs |
| **ChromaDB** | Vector database used to store and search the social-lab knowledge base locally |
| **Ollama** | Local LLM runtime — runs models like phi3:mini or llama3.2:3b on your machine with no cloud or API cost |
| **Embedding** | A numerical representation of text that allows semantic (meaning-based) search |
| **Chunk** | A segment of a document (800 chars with 150-char overlap) used as the unit of retrieval in the RAG |
| **Upsert** | Insert or update — used in ChromaDB to add new chunks without duplicating existing ones |
| **VRAM** | Video RAM — memory on your GPU (RX 6500 XT = 4GB); small models (phi3:mini, llama3.2:3b) fit here and run fast |
| **LCP** | Largest Contentful Paint — Google's metric for how fast the main content of a page loads (target: <2.5s) |
| **CLS** | Cumulative Layout Shift — measures visual stability; elements jumping around on load (target: <0.1) |
| **TTFB** | Time to First Byte — how fast the server responds (target: <600ms on good hosting) |
| **INP** | Interaction to Next Paint — responsiveness metric that replaced FID in 2024 (target: <200ms) |
| **Core Web Vitals** | Google's set of real-world performance metrics: LCP, CLS, INP |

---

## Content Terms

| Term | Definition |
|------|-----------|
| **Hook** | The first 0–3 seconds of a video — determines whether viewers keep watching |
| **3-Sec Hold Rate** | % of viewers who watch past the 3-second mark — proxy for hook effectiveness |
| **Save Rate** | Saves ÷ Views — the strongest algorithm signal on TikTok and Instagram Reels |
| **Faceless** | Video style with no camera — screen-share, terminal, or text overlay only |
| **A-Roll** | Primary footage (main screen, speaker) |
| **B-Roll** | Secondary footage (cutaways, overlays, close-ups) |
| **CTA** | Call to Action — what you ask the viewer to do at the end ("Comment X", "Link in bio", "Follow") |
| **Comment Trigger** | A CTA format ("Comment 'SPEED'") that drives DM automation and algorithm engagement on TikTok |
| **Series** | A recurring content format with a defined style, ICP, and topic area — BADGR has 4 |
| **Wave 1** | The first batch of 12 scripts — 3 per series |
| **Archetype** | The template definition for a series — ICP, platforms, length, visual style, required assets |

---

## Compliance & Legal Terms

| Term | Definition |
|------|-----------|
| **HIPAA** | Health Insurance Portability and Accountability Act — governs PHI; relevant to medical/dental clients' websites |
| **PHI** | Protected Health Information — names, diagnoses, contact info tied to health data; must not appear in URLs or unsecured forms |
| **ADA** | Americans with Disabilities Act — applies to websites via case law; requires accessible design |
| **WCAG** | Web Content Accessibility Guidelines — the technical standard for ADA web accessibility (target: WCAG 2.1 AA) |
| **axe DevTools** | Free Chrome extension for automated ADA/WCAG scanning |
| **Lighthouse** | Google's open-source tool for auditing performance, accessibility, SEO, and best practices |
| **CICD** | In BADGR context: Continuous Inspection, Compliance, and Delivery — not CI/CD in the traditional DevOps sense |

# phase1_ops_manual

Source: BADGR_Phase1_FullOpsManual.pdf (converted and structured 2026-04-18)

---

## What Phase 1 Is

A 90-day flagship offer for Atlanta law firms or small medical/dental practices: a 14-day "Lead Leak & Compliance Fix" built on a locked ICP, strict daily schedule, and a gate model that prevents expansion before profitability is proven.

**One ICP. One offer. One 90-day sprint.**

---

## 90-Day Timeline

| Period | Focus |
|--------|-------|
| Week 1–2 | Client 1 — Scan → Fix → Proof |
| Week 3–4 | Client 2 + testimonial collection from Client 1 |
| Week 5–8 | Clients 3–5 + case summary documentation |
| Week 9–12 | Gate 1 evaluation; begin Phase 2 planning if criteria met |

---

## Daily Schedule (Monday–Friday)

| Block | Activity |
|-------|----------|
| Morning (8:30–10:00 AM) | Pull lead log; identify top 5 worst sites; send 5 personalized emails |
| Delivery block (10:00 AM–12:00 PM) | Active scan, fix, or proof work for current client |
| Calls block (12:00–1:30 PM) | Discovery calls, client check-ins, testimonial follow-ups |
| Build block (1:30–3:30 PM) | Build/document systems, templates, scripts, automations |
| Study block (3:30–4:30 PM) | Research, platform updates, case review, competitor monitoring |
| Content slot (Tue/Thu/Sat 4:30–5:00 PM) | Short-form recording session (no prospecting time sacrificed) |
| Quiz / RAG update (4:30–5:00 PM Mon/Wed/Fri) | Generate quiz questions; update local knowledge base |
| Shutdown ritual (5:00 PM) | Close all tabs; log day's output; set tomorrow's top 3 tasks |

---

## Client Delivery Phases

### Scan (Days 1–3)
- Ingest client URL and prior notes
- Run CICD Verification Prompt: SEO meta, Core Web Vitals, CTA placement, compliance pages
- Lighthouse mobile + desktop scans — extract LCP, INP, CLS, TTFB
- ADA/WCAG checks via axe DevTools: contrast, keyboard nav, alt text, landmark structure
- HIPAA web presence (medical/dental): PHI in URLs, SSL status, privacy policy visibility, third-party scripts
- Manual CTA audit: click every button, submit every form, test every phone link
- Output: timestamped findings list, page-level, priority-ranked

### Fix (Days 4–10)
- Prioritize by impact × effort. First tier always:
  1. Mobile speed and stability (LCP, CLS, TTFB)
  2. Working CTAs and forms
  3. Core trust/legal pages (privacy, terms, contact)
- For each fix: draft improved copy, suggest layout changes, propose technical changes for implementation
- Log every fix: date / page / issue / change description / before-after screenshots
- Re-run CICD checks after each major fix to confirm flag cleared
- Human approval required before: DNS changes, production deploys, legal text edits

### Proof (Days 11–14)
- Full re-run of Lighthouse scans — extract before/after delta
- Assemble Lead Leak Compliance Report:
  - Executive summary (business language, no jargon)
  - Before/after metrics table (speed, forms, CTAs, compliance items)
  - Narrative case notes for 3+ key pages
  - 3 "Next Steps" upsell options
- Draft testimonial request copy for the client
- Verify client folder completeness:
  - [ ] Scan artifacts (Lighthouse PDFs, axe reports)
  - [ ] Fix log with before/after screenshots
  - [ ] Lead Leak Compliance Report
  - [ ] Testimonial (or follow-up sent)
  - [ ] Invoice paid
  - [ ] Hours log

---

## Pre-Flight Checklist (Before Each Client Engagement)

- [ ] Client URL confirmed; access granted or screen-share arranged
- [ ] Signed engagement letter on file
- [ ] Lighthouse baseline captured (mobile + desktop PDFs saved)
- [ ] ADA/WCAG baseline noted
- [ ] HIPAA web presence check noted (medical/dental only)
- [ ] Fix scope agreed in writing (top 5–10 issues only — no scope creep)
- [ ] Client folder created: `/clients/[name]/scans /fixes /reports /comms`
- [ ] Stripe invoice sent and paid (or payment plan confirmed in writing)

---

## Gate Model

### Gate 0 (Operating State)
- One ICP, one vertical, one offer per 90-day cycle
- No new tools until Gate 1
- No new platforms or automations until Gate 1
- Daily schedule is locked

### Gate 1 (Exit Criteria — all must be true)
- 3–5 paying Atlanta clients completed with full delivery
- 3+ testimonials collected (written or video)
- 3+ case summaries documented (anonymized, publishable)
- Hours × rate = profitable (not break-even)

### After Gate 1
- Evaluate adding a second vertical or second offer
- Begin Phase 2 planning: retainers, expanded ICP, or regional expansion
- Update `00_admin/change-log.md`

---

## Operating Constitution (7 Rules)

1. Client safety and auditability over speed
2. One ICP and one offer per 90-day sprint — no exceptions
3. No irreversible changes (DNS, production deploys, legal text) without explicit human approval
4. All client data confidential — no PII to third-party APIs without written opt-in
5. No new tools until Gate 1 — complexity is the enemy at this stage
6. Fix log and compliance report required for every single engagement
7. Daily quiz/RAG update is non-negotiable — knowledge compounds and this is the moat

---

## Failure Modes and Diagnostics

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| No response to 5 daily emails | Wrong ICP or weak subject lines | Rewrite subject + first line; tighten ICP filter |
| Discovery calls not converting | Price anchoring too early | Lead with findings, not price |
| Fix taking >10 days | Scope creep | Re-scope; lock change order in writing |
| Client not giving testimonial | Asked at wrong moment | Ask day 12 during proof walkthrough, not day 14 |
| Lighthouse score unchanged after fix | Wrong fix priority | Re-run CICD; check PageSpeed Insights for hidden issues |
| Hours not profitable | Underscoped discovery | Add discovery call mandatory before any engagement |
| Content slots being skipped | Delivery pressure | Remember: Tue/Thu/Sat 4:30–5:00 PM is protected time |

---

## RAG / Quiz System

- End of each day: generate 3–5 quiz questions from the day's work
- Store questions + answers in the local knowledge base
- Weekly: query the RAG for gaps — "What do I not know about HIPAA web compliance?"
- This is the compounding advantage — knowledge builds faster than competitors can copy the system

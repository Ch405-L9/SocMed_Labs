# badgr_bolt_overview

Source: BADGR Bolt Dev Context.md, BADGR_Bolt_Final_Report.md, BADGR Bolt Pricing And Readme.md, Marketing&FULLplatformNarratives.txt. Last updated 2026-04-18.

---

## What It Is

BADGR Bolt is an Android speed-reading app built around Rapid Serial Visual Presentation (RSVP) and Optimal Recognition Point (ORP) techniques. It flashes words in a fixed focal point, highlighting the optimal recognition letter so eyes stay anchored, reducing saccades and fatigue.

**Tagline:** Advanced RSVP Speed Reader for Real-World Reading
**Platform:** Android 8.0+
**GitHub:** github.com/Ch405-L9/ReaderRSVP (MIT-licensed core)
**Business model:** Open-Core Freemium

---

## Honest Positioning

Most speed-reading apps promise "5x faster reading" while ignoring evidence that aggressive RSVP hurts comprehension on complex texts. BADGR Bolt takes an engineering-driven approach: chunk reading (1–4 words), punctuation-aware pauses, and a Performance Tracker that ties speed increases to measurable comprehension — not raw WPM alone.

The product is a lab for discovering your personal optimal balance of speed and understanding, not a speed-hack gimmick.

---

## Core Features

| Feature | Description |
|---------|-------------|
| RSVP + ORP engine | Custom Kotlin engine (OrpEngine.kt) calculates optimal focal point per word |
| Chunk reading | 1–4 word chunks; punctuation-aware pauses preserve meaning |
| File import | TXT (Phase 1); PDF, EPUB, DOCX, and images via OCR (Phase 2 backend) |
| Performance Tracker | Session logging: WPM, duration, rewinds, streaks, personal bests |
| Achievements + Bolt Rank | Milestones tied to comprehension and consistency, not raw speed |
| Visual comfort controls | System/light/dark themes; 6 fonts; ORP color picker |
| Firebase Auth + Firestore | Cloud sync for library and progress (Phase 2) |

---

## Pricing

| Tier | Price | Limits | Key Features |
|------|-------|--------|-------------|
| Free (Forever) | $0, no ads | 5 active library items; .txt and basic .pdf; local only | RSVP/ORP engine, SAF file import, adjustable WPM, punctuation delay, basic themes, most-recent-session stats |
| Free + Account | $0 | Up to 15 library items; cloud backup of settings/progress | 7-day Pro trial unlocked once per account |
| Pro Monthly | $3.99/mo | Unlimited items; multi-device sync | EPUB + full PDF, advanced stats dashboard, reading streaks, custom themes, font presets, TTS, priority support |
| Pro Yearly | $24.99/yr (~48% vs. monthly) | Same as Pro Monthly | Best-value for serious readers/students |
| Lifetime Pro | $49.99 one-time | Same as Pro Yearly; tied to Google account | For users who distrust subscriptions |

---

## Build Status

| Phase | Status | What's Included |
|-------|--------|----------------|
| Phase 1 MVP | Complete | RSVP/ORP engine, .txt import via SAF, basic settings, zero-permission local-only privacy posture |
| Phase 2 | Planned | Firebase Auth/Firestore sync, Google Play Billing, EPUB/PDF parsing, Performance Tracker, advanced theming, TTS, onboarding redesign |

Legal and store docs (MIT license, Privacy Policy, Terms of Service, Google Play Data Safety) are drafted but need updating to reflect accounts, cloud sync, and monetization before public launch.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| App | Kotlin + Jetpack Compose |
| Auth + Sync | Firebase Auth + Firestore (Phase 2) |
| Billing | Google Play Billing Library (Phase 2) |
| File conversion | Python / FastAPI backend (OCR, EPUB/PDF parsing) |
| Engine | OrpEngine.kt — custom ORP focal point calculator |

---

## Business Model: Open-Core Freemium

- **Open-source core (MIT):** RSVP engine, Free-tier UI, .txt/.pdf import, basic settings — public on GitHub.
- **Proprietary Pro features:** Performance Tracker, cloud sync, advanced file formats, TTS — compiled binary distributed via Google Play only.
- **Competitive position:** Above barebones speed-reading utilities (Speedy Reader, Reedy); below full content ecosystems (Kindle, Kobo). Differentiator is privacy, local file control, and analytics rather than content sales.

---

## Content / Social Fit

BADGR Bolt is a RAG Lab series candidate for social content — live ORP demos, "how RSVP actually works" myth-busts, and before/after comprehension comparisons are high-save formats on YouTube Shorts and TikTok. The "no hype" technical angle differentiates it from competitor speed-reading content.

---

## Key Contacts / Repos

| Item | Detail |
|------|--------|
| GitHub | github.com/Ch405-L9/ReaderRSVP |
| Local dev path (suggested) | /home/t0n34781/Projects/badgr_bolt |
| Default AI model for code | qwen2.5-coder:7b (local via Ollama) |
| Default AI model for planning | llama3.2:latest or Qwen omni variant |

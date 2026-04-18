# ai_disclosure_policy

## BADGR AI Use Disclosure

BADGR Technologies uses AI tools in content creation, research, and client deliverable drafting. This policy defines when and how AI use is disclosed.

---

## When Disclosure Is Required

| Context | Disclosure Required | Format |
|---------|-------------------|--------|
| Client deliverable (report, copy, templates) | Yes | Written note in deliverable footer |
| Social media video script (AI-drafted) | Yes — in caption or comments | "AI-assisted. Human-reviewed." |
| Outbound email (AI-drafted) | Yes — in email footer | See template below |
| Blog post or article (AI-assisted) | Yes | Author note at end of post |
| Internal ops (fix logs, checklists) | No | N/A |
| RAG-generated answer (operator queries own knowledge base) | No | N/A |

---

## Standard Disclosure Language

**Client deliverables:**
> "Portions of this deliverable were drafted with AI assistance (Claude / local Ollama) and reviewed by BADGR Technologies staff. All recommendations reflect BADGR's professional judgment."

**Email footer:**
> "This email may have been drafted with AI assistance and reviewed before sending. BADGR Technologies LLC."

**Social caption:**
> "AI-assisted. Human-reviewed. | Not legal advice."

**Video overlay (optional for transparency):**
> "Script drafted with AI. Reviewed and recorded by Brandon Grant, BADGR Technologies."

---

## AI Tools in Use (Disclosed)

| Tool | Use Case | Data Privacy |
|------|---------|-------------|
| Claude (Anthropic) | Script drafting, report writing, research | No client PII shared |
| Ollama (local) | RAG queries, SOP lookups | All data stays on local machine |
| ChromaDB (local) | Vector search over /social-lab/ docs | No cloud storage |
| Submagic | Caption generation for videos | Video content only, no PII |
| Pika Labs | AI video generation (optional) | Creative assets only |

---

## What We Don't Do

- We do not feed client PII into cloud AI models without explicit written consent
- We do not represent AI-generated content as human-written when asked directly
- We do not use AI to generate fake testimonials, case results, or client quotes

# SYSTEM CHANGELOG — BADGRTechnologies LLC Social Profile Build System

Standard: SOCIAL_PROFILE_BUILD_STANDARD_v2 | Location: /home/t0n34781/Desktop/brand/

---

## v2.1 — 2026-04-20

### Platforms Completed (Phase 1 — all 5 done)
- TikTok    ✓ COMPLETE
- X         ✓ COMPLETE
- Facebook  ✓ COMPLETE
- YouTube   ✓ COMPLETE
- Instagram ✓ COMPLETE
- LinkedIn  — DEFERRED (post-Gate 1)

### Standard Additions (v2.0 → v2.1)
- §8  added: Brand Naming Rules (BADGRTech / BADGRTechnologies LLC, forbidden forms list)
- §9  added: Statistics & Proof Standards (no fabricated numbers, results vary)
- §10 added: ICP Reference (ATL law/medical Phase 1 lock, source: BADGR_Phase1_FullOpsManual.pdf)
- §11 added: Platform Rollout Order (sequence + rationale)
- §12 added: Reusable Bolt Beta Reference Block (3-step links, per-platform clickability rules)
- §13 updated: Checklist expanded (10 items — brand naming + stats + ICP + Bolt links)
- §14 added: Pre-Execution Guardrail Gate (file checks + model routing + content flags)
- §15 added: Run Checkpoint Structure (build_log.json schema)

### Model Routing (codified in badgr_brand_rules.model_routing)
- Copy generation:      gemma3:4b  (pulled 2026-04-20)
- Summarization:        mistral:latest
- Code/structured data: qwen2.5-coder:7b
- Routing/utility:      llama3.2:3b
- Fallback:             gemma3:4b
- Reason: mistral:latest failed structured generation on X profile — echoed instructions verbatim twice. gemma3:4b confirmed replacement.

### Tools Schema Changes (social-profile-tools.json)
- All 8 tools: failure_modes + dependencies fields added
- badgr_brand_rules: model_routing section added (6 keys: copy_generation, summarization, code_and_structured_data, routing_and_utility, fallback, available_models)
- badgr_brand_rules.guardrails: no_emojis rule added
- badgr_brand_rules.inputSchema.section enum: model_routing value added
- ollama_profile_build.output_schema.validation: 3 numeric scores added (brand_alignment_score, compliance_score, copy_quality_score) with deduction formulas
- ollama_profile_build.inputSchema.model description: updated to reference badgr_brand_rules model_routing

### New Files
- /home/t0n34781/Desktop/brand/build_log_template.json — run trace template, written to each post kit after every build
- /home/t0n34781/Desktop/brand/SYSTEM_CHANGELOG.md — this file

### Violations Resolved Across Platform Builds
| Platform  | Model       | Violation                                        | Fix                                        |
|-----------|-------------|--------------------------------------------------|--------------------------------------------|
| Instagram | gemma3:4b   | Emoji use (➡️) in 3 posts                       | All removed                                |
| Instagram | gemma3:4b   | Fabricated Bolt product description              | Full rewrite (beta Android tester app)     |
| Instagram | gemma3:4b   | Bio 176 chars (over 150 limit)                   | Trimmed to 120                             |
| YouTube   | gemma3:4b   | Channel name 116 chars (over 100 limit)          | Trimmed to "BADGRTech" (9)                 |
| Facebook  | gemma3:4b   | About 350+ chars (over 255 limit)                | Rewritten to 184                           |
| X         | mistral      | Structured generation failure (echoed prompt)    | Switched to claude-authored                |
| Multiple  | mistral      | Question openers across platforms                | Replaced with statement-first              |
| Multiple  | mistral      | Fabricated stats ($50k saved, specific scores)   | Replaced with process-proof + results vary |
| Multiple  | mistral      | "BADGR Technologies" (with space)                | Corrected to BADGRTech                     |

### Build Items Open
- BUILD_ITEM: badgrtech.com/links mobile landing page
  Spec: /home/t0n34781/Desktop/brand/tik_tok_post_kit/BUILD_ITEM_link_in_bio_page.txt
  Blocks: TikTok + Instagram Bolt beta clickable CTAs (no clickable links in captions)
  UTM params: ?utm_source=tiktok&utm_medium=bio

### Gate 1 Requirement (before LinkedIn activation)
- 3–5 ATL clients signed
- 3 testimonials collected
- Source: BADGR_Phase1_FullOpsManual.pdf

---

## v2.2 — 2026-04-20

### TikTok Profile — Constraint Compliance Revision

**Bio:**
- Rewritten to TikTok-native format: pain → outcome → CTA, ≤80 chars, plain text only
- Primary: "ATL sites losing leads? We fix it in 14 days. ↓ Start here" (59 chars)
- Alt:     "ATL businesses losing leads? We fix it fast. ↓ Get audit" (57 chars)
- Bio question opener retained as intentional TikTok exception (conversion hook)

**Handle:** @badgrtechnologies → @badgrtech25 (platform-registered TikTok handle)

**Link system:** badgrtech.com/links (unbuilt) → linktr.ee/badgrtech (Linktree interim, ACTIVE)

**Hashtag strategy overhaul:**
- Old: branded-only (too narrow, low discovery)
- New: 5 discovery + 2 branded per post minimum. Alt pool for rotation.
- Discovery pool: #WebDesign #SEO #SmallBusiness #AtlantaBusiness #LocalSEO + alt pool
- Rule added to standard: never exceed 3 branded per post

**Format fix:** [H1]/[BODY] markup tags removed from TikTok copy-paste output — plain text only

**Image standard clarified:**
- Master PNG (official_badgr-logo_px512.png): transparent, untouched, never modified
- Platform outputs (profile photos, banners): brand bg (#0E305F) padding is structural and correct
- Distinction codified in §2 of SOCIAL_PROFILE_BUILD_STANDARD_v2.txt

### Standard Changes (v2.1 → v2.2)
- §2: Image handling section updated — master vs platform output distinction explicit
- §4B: Platform format rules added (TikTok = plain text only; per-platform rules)
- §8: Platform handles table added (TikTok @badgrtech25 vs @badgrtechnologies elsewhere)
- §9: Hashtag strategy section added (discovery-first, ratio rule, alt pool)
- Standard version bumped to 2.2

---

## v2.0 — 2026-04-20 (initial build)

### Established
- SOCIAL_PROFILE_BUILD_STANDARD_v2.txt created
- Dual output format mandated: JSON (machine) + copy-paste (human)
- Typography contract: Goldman Bold (H1) / Satoshi (H2) / Inter (body)
- Image handling: non-destructive, originals untouched, ImageMagick only
- Learning loop tags per content piece: hook_type, format, tone, content_pillar, estimated_engagement_tier, data_source
- social-profile-tools.json: 7 tools + badgr_brand_rules reference tool
- Platform image specs embedded in ollama_image_spec
- Character limits per platform embedded in ollama_profile_build.platform_field_limits

### Image Asset Ledger (all COMPLETE, originals untouched)
| Platform  | Asset               | Output Path                                                              | Dimensions   |
|-----------|---------------------|--------------------------------------------------------------------------|--------------|
| TikTok    | profile_photo       | tik_tok_post_kit/profile_photo_200x200.jpg                               | 200x200 JPG  |
| X         | profile_photo       | x_twitter__post_kit/profile_photo_400x400.jpg                            | 400x400 JPG  |
| X         | banner              | x_twitter__post_kit/banner_1500x500.jpg                                  | 1500x500 JPG |
| Facebook  | profile_photo       | facebooj__post_kit/profile_photo_170x170.jpg                             | 170x170 JPG  |
| Facebook  | cover               | facebooj__post_kit/cover_820x312.jpg                                     | 820x312 JPG  |
| YouTube   | profile_photo       | youtube__post_kit/profile_photo_800x800.png                              | 800x800 PNG  |
| YouTube   | banner              | youtube__post_kit/banner_2560x1440.jpg                                   | 2560x1440 JPG|
| Instagram | profile_photo       | instagram_post_kit/profile_photo_320x320.jpg                             | 320x320 JPG  |

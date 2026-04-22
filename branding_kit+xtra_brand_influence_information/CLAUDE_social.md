# BADGRTech Social Profile Workspace – CLAUDE.md

## 0. Purpose

This workspace is specialized for **social media profile systems** (TikTok first, other platforms later).
Your job is to design, validate, and finalize production‑ready profile assets while minimizing cloud token usage.

Core principles:
- Local‑first: heavy generation is handled by local Ollama models via the `badgr_pipeline` MCP tool.
- Claude‑as‑architect: you focus on planning, quality control, and edge cases.
- Boil the ocean: for each request, aim to fully complete the profile artifact (bio, name, link, image spec, hashtags) within scope.

---

## 1. Roles & Tools

### 1.1 Roles

- **Claude (you)**
  - Understand user goals and platform context.
  - Call `badgr_pipeline` for classification and execution.
  - Review and patch outputs, ensuring brand and platform compliance.

- **`badgr_pipeline` MCP server**
  - Control plane between you and local models.
  - Stages:
    - `classify` – categorize the request into `task_type`, `complexity`, `requires_rag`, `domain`.
    - `route` – map classification to specific local models and tools.
    - `execute` – call social tools (e.g., `ollama_generate`, `ollama_validate`) using `social-profile-tools.json`.
    - `guard` – enforce character limits, emoji rules, forbidden phrases, and brand constraints.
    - `cascade` – small → larger local models, then mark when you must review.
    - `respond` – return compact JSON with content, scores, violations, and readiness.

- **Local models (via Ollama)**
  - Gemma 3 4B: copywriting, bios, short text.
  - Mistral: summarization, compression, hashtag idea expansion.
  - Llama 3.2 3B / Phi: lightweight classification, routing.
  - (Other models may be available; routing logic is inside `badgr_pipeline`.)

You never call local models directly; always go through `badgr_pipeline`.

---

## 2. Mandatory Classification

Every user request must go through classification before any heavy tool use.

- First step for any task:
  - Call `badgr_pipeline.classify()` with the raw user request.
- Do not call generation or validation tools until classification is complete.

Expected classification shape (conceptual):

```json
{
  "task_type": "small_edit | generation | profile_setup | asset_pipeline | analysis",
  "complexity": "low | medium | high",
  "requires_rag": true | false,
  "domain": "social"
}
```

If classification is missing or unclear, request clarification from the user or rerun classification. Do not bypass this step.

---

## 3. Routing & Execution Policy (Social Profiles)

After classification, you call `badgr_pipeline.execute()` with the classification result and any necessary snippets (existing bio, screenshot description, etc.). The server applies routing rules and returns a compact result.

### 3.1 Task types for social profiles

Use these interpretations:

- `small_edit` – small bio tweak, hashtag swap, minor text change.
- `generation` – new bios, variations, bulk caption/headline generation.
- `profile_setup` – full profile pass (name, bio, link strategy, hashtags, image spec).
- `asset_pipeline` – image spec/commands for profile photos, banners.
- `analysis` – diagnose why a profile is under‑performing; return a prioritized fix list.

### 3.2 Execution policy

- **Default: local_first**
  - Assume local models can handle:
    - bios, hooks, CTAs;
    - hashtag sets;
    - profile image specs and ImageMagick command drafts;
    - profile teardown/analysis summaries.

- Escalate to deeper reasoning (cloud) only when:
  - classifier marks `complexity = high` or `requires_rag = true`, or
  - cascade returns low confidence or repeated violations, or
  - the user explicitly wants your (Claude’s) strategic reasoning.

You rely on `badgr_pipeline` for which specific model to use per task. Do not override model choices yourself.

---

## 4. Pipeline Output & How You Use It

`badgr_pipeline.execute` returns a compact JSON result. Conceptual shape:

```json
{
  "c": "content",
  "s": { "check_name": 0-100 },
  "v": ["violation_code"],
  "r": true,
  "conf": 0.0,
  "err": ["error_tag"],
  "needs_claude_review": true
}
```

Interpretation:

- `c` – content (bio, name suggestions, hashtag sets, image command, etc.).
- `s` – per‑check scores (e.g., `char_limit`, `fluff`, `platform_match`).
- `v` – violations codes (e.g., `char_overflow`, `emoji_disallowed`, `forbidden_phrase`).
- `r` – whether pipeline considers this ready for direct use.
- `conf` – 0–1 confidence score for the result.
- `err` – error tags, if any (e.g., tool failure, RAG miss, validation error).
- `needs_claude_review` – pipeline requests your attention.

### 4.1 When result is ready

If `r === true` and `needs_claude_review === false`:
- Skim `c`.
- Optionally tighten language or ordering.
- Return final content/artifact to the user.

### 4.2 When result needs review

If `needs_claude_review === true` or `r === false`:
- Focus only on:
  - the provided content `c`;
  - violations `v` and errors `err`;
  - any platform/brand specs referenced (e.g., TikTok bio limit, safe zone rules).
- Fix issues by:
  - rephrasing bios/CTAs to fit limits;
  - adjusting hashtags for discovery vs brand balance;
  - editing image specs/commands to meet standards.
- Return a final, clean artifact that resolves violations.

Do not regenerate everything from scratch when targeted edits will suffice.

---

## 5. Boil the Ocean – Social Profile Standard

The full "Boil the ocean" directive lives in `memory-bank/systemPatterns.md`. For social profiles, apply it as:

- Deliver a **complete profile** when user intent implies it:
  - optimized Name, Bio, Link strategy, Hashtags, and Image spec.
- Prefer a smaller, clearly defined profile (one account, one platform) fully optimized over many platforms done half‑way.
- Search/inspect existing profile context before rewriting:
  - if prior bio, name, or screenshots are available, use them.
- Validate before shipping:
  - enforce character limits, platform rules, brand constraints.
- Test via simple reasoning:
  - "In 3 seconds, does a scroller know what this account does, who it’s for, and where to click?" If not, refine.

You are responsible for shipping a conversion‑ready profile, not just text that "fits".

---

## 6. Platform‑Specific Guidance (TikTok First)

Use `social-profile-tools.json` for platform constants and constraints.

For TikTok, assume:
- Bio max: ~80 characters (optimize for this).
- Bio pattern: **pain → outcome → CTA**.
- Name: include brand + locality/keyword where possible (e.g., `BADGRTech | Atlanta SEO`).
- Link: treat as funnel entry; match CTA language in bio.
- Hashtags: mix branded + discovery tags.
- Profile image: square upload, circle display; use safe zone and brand background.

Example TikTok bio standard:
- "ATL businesses losing leads? We fix it in 14 days. ↓ Start here"

Example TikTok image spec (conceptual):
- Canvas: 720×720 px.
- Safe zone: center 80–85%.
- Background: `#0E305F`.
- No small text; high‑contrast logo centered.

---

## 7. Context & Files

Use the project files instead of re‑explaining rules in the chat.

- `social-profile-tools.json`
  - Contains tool definitions and platform limits for social tasks.
  - Use it indirectly via `badgr_pipeline`; do not paste it into chat.

- `memory-bank/systemPatterns.md`
  - Contains full system architecture and "Boil the ocean" directive.

- `memory-bank/productContext.md`
  - Explains why the Ollama MCP server exists and how it should feel to use.

When you need details, request the relevant file or section; do not pull entire trees if not necessary.

---

## 8. Token & Context Discipline (Social Focus)

- For `small_edit` tasks (bio tweaks, hashtag edits):
  - Stay within the smallest snippet required.
  - Do not run full profile analysis or RAG.
- For `profile_setup` tasks:
  - Work from the user’s description and any existing profile data.
  - Use `badgr_pipeline` for bulk generation.
  - Perform one thorough pass, not many micro‑steps.
- Keep your answers concise:
  - Default to 1–2 short paragraphs or up to 5 bullets when user doesn’t request a deep dive.

When the user explicitly asks for a full profile system or deep audit, you may expand, but still route heavy generation through `badgr_pipeline` and keep schemas out of the chat.

---

## 9. Example Workflows (How You Should Behave)

### 9.1 New TikTok profile from scratch

1. Classify request via `badgr_pipeline.classify()`.
2. Call `badgr_pipeline.execute()` with `task_type = profile_setup`.
3. Read output `c`:
   - It should contain proposed Name, Bio, Link strategy, Hashtags, and Image spec.
4. Fix any issues flagged in `v`/`err`, refine language, then return:
   - final Name,
   - final Bio (≤80 chars),
   - link recommendation,
   - hashtag set,
   - profile image command/spec (if requested).

### 9.2 Bio tweak for existing profile

1. Classify as `small_edit`.
2. Call `badgr_pipeline.execute()` with:
   - existing bio,
   - requested change.
3. Ensure char limit and pattern (pain → outcome → CTA) are preserved.
4. Return only the updated bio (and brief rationale if helpful).

### 9.3 Cross‑platform extension later

When asked to extend to other platforms (X, YouTube, etc.):
- Reuse the TikTok logic:
  - platform limits and field names come from `social-profile-tools.json`.
- Design full profiles for each platform, respecting each one’s constraints.
- Still route heavy generation locally; you perform glue logic and quality checks.

---

This CLAUDE.md governs how you operate in this workspace. Follow it strictly so that local models do the bulk work, the `badgr_pipeline` enforces rules, and you make sure each profile asset is complete, on‑brand, and conversion‑ready.

================================================================================  >><< Implement the below As needed Per The Request >>

badgr_pipeline:
==============\/

The missing piece is the actual badgr_pipeline tool in your MCP server. Below is a TypeScript skeleton you can drop into src/badgr_pipeline.ts (or similar), plus a one-liner to wire it into your existing index.ts. This is designed to be safe to paste and then iteratively wire into your real Ollama tools.

All comments are inline so you can see exactly what each part does.

1. src/badgr_pipeline.ts – pipeline tools (classify + execute)
ts
// src/badgr_pipeline.ts
// BADGRTech social-profile pipeline layer
// - Exposes two MCP tools: `badgr_classify` and `badgr_execute`.
// - Intended to orchestrate existing Ollama-based tools
//   (e.g. `ollama_generate`, `ollama_validate`) using social-profile-tools.json.
// - Implements local-first routing, simple guards, and a cascade stub.
// - NOTE: This file is a skeleton. TODOs mark where you wire into your real tools.

import { z } from "zod";
import type { McpServer, Tool } from "@modelcontextprotocol/sdk/server";

// ----------------- Types & Schemas -----------------

// High-level task types for social profile work
export const TaskTypeEnum = z.enum([
  "small_edit",
  "generation",
  "profile_setup",
  "asset_pipeline",
  "analysis",
]);

export type TaskType = z.infer<typeof TaskTypeEnum>;

export const DomainEnum = z.enum(["social"]);

export const ComplexityEnum = z.enum(["low", "medium", "high"]);

export const ClassificationSchema = z.object({
  task_type: TaskTypeEnum,
  complexity: ComplexityEnum,
  requires_rag: z.boolean(),
  domain: DomainEnum,
});

export type Classification = z.infer<typeof ClassificationSchema>;

// Output schema for badgr_execute
export const BadgrPipelineOutputSchema = z.object({
  c: z.string(), // content
  s: z.record(z.string(), z.number().min(0).max(100)), // scores per check
  v: z.array(z.string()), // violation codes/messages
  r: z.boolean(), // ready_for_use
  conf: z.number().min(0).max(1), // confidence 0-1
  err: z.array(z.string()), // error tags
  needs_claude_review: z.boolean(),
});

export type BadgrPipelineOutput = z.infer<typeof BadgrPipelineOutputSchema>;

// Input schema for badgr_classify
export const BadgrClassifyInputSchema = z.object({
  // Raw user request or Claude's task description
  request: z.string(),
});

// Input schema for badgr_execute
export const BadgrExecuteInputSchema = z.object({
  classification: ClassificationSchema,
  // primary text content (e.g. existing bio, description of account, etc.)
  content: z.string().optional(),
  // optional platform hint (e.g. "tiktok")
  platform: z.string().optional(),
  // optional extra context (JSON-stringified if needed)
  context: z.unknown().optional(),
});

// ----------------- Routing Table (social-specific) -----------------

// For now, keep a simple in-code routing table.
// Later you can move this into a JSON config or reuse social-profile-tools.json.
const routingTable: Record<
  TaskType,
  { model: string; fallbackModel?: string; useRag: boolean }
> = {
  small_edit: {
    model: "gemma3:4b",
    useRag: false,
  },
  generation: {
    model: "gemma3:4b",
    fallbackModel: "llama3.1:8b",
    useRag: false,
  },
  profile_setup: {
    model: "gemma3:4b",
    fallbackModel: "llama3.1:8b",
    useRag: false,
  },
  asset_pipeline: {
    model: "mistral:latest",
    useRag: false,
  },
  analysis: {
    model: "mistral:latest",
    useRag: false,
  },
};

// ----------------- Classification Logic -----------------

// NOTE: This is intentionally simple and deterministic.
// You can replace this with a local model-based classifier later if needed.
function classifyText(request: string): Classification {
  const lower = request.toLowerCase();

  if (lower.includes("tiktok") && lower.includes("profile")) {
    // micro-edits to existing bio
    if (lower.includes("bio") && (lower.includes("tweak") || lower.includes("edit"))) {
      return {
        task_type: "small_edit",
        complexity: "low",
        requires_rag: false,
        domain: "social",
      };
    }

    // profile image / avatar work
    if (
      lower.includes("image") ||
      lower.includes("avatar") ||
      lower.includes("profile photo")
    ) {
      return {
        task_type: "asset_pipeline",
        complexity: "medium",
        requires_rag: false,
        domain: "social",
      };
    }

    // audits / teardown & fix plan
    if (
      lower.includes("audit") ||
      lower.includes("analyze") ||
      lower.includes("fix plan") ||
      lower.includes("diagnose")
    ) {
      return {
        task_type: "analysis",
        complexity: "medium",
        requires_rag: false,
        domain: "social",
      };
    }

    // default TikTok profile: full setup
    return {
      task_type: "profile_setup",
      complexity: "medium",
      requires_rag: false,
      domain: "social",
    };
  }

  // Fallback: generic copy generation in social domain
  return {
    task_type: "generation",
    complexity: "medium",
    requires_rag: false,
    domain: "social",
  };
}

// ----------------- Guard & Cascade Helpers -----------------

interface GuardResult {
  output: BadgrPipelineOutput;
}

// Basic guard stub:
// - trims content
// - length-based score
// - simple emoji check
// TODO: extend with:
// - platform-specific char limits (e.g. 80 chars for TikTok bio)
// - forbidden phrases
// - brand checks via a dedicated validation tool
function basicGuard(content: string): GuardResult {
  const trimmed = content.trim();
  const violations: string[] = [];
  const scores: Record<string, number> = {};

  // Example: simple length-based score (penalize very long content)
  scores["length"] = Math.max(0, Math.min(100, 100 - Math.max(0, trimmed.length - 200)));

  // Emoji check (simple approximation)
  const emojiRegex =
    /[\u{1F000}-\u{1FFFF}]|[\u{2600}-\u{27BF}]|[\uFE00-\uFE0F]/u;
  if (emojiRegex.test(trimmed)) {
    violations.push("emoji_present");
    scores["emoji"] = 0;
  } else {
    scores["emoji"] = 100;
  }

  const conf = scores["length"] / 100;

  const output: BadgrPipelineOutput = {
    c: trimmed,
    s: scores,
    v: violations,
    r: violations.length === 0,
    conf,
    err: [],
    needs_claude_review: violations.length > 0 || conf < 0.7,
  };

  return { output };
}

// ----------------- Model Execution Stub -----------------

// TODO: Wire this into your real Ollama MCP tools.
// Rough outline of what you will do here:
// - For text (bios, hashtags, etc.), call your `ollama_generate` tool
//   with `model = routingTable[task.task_type].model` and constraints
//   from social-profile-tools.json.
// - For validation, call `ollama_validate` where appropriate.
// - For RAG (later), call `ollama_rag_query` when `useRag` is true.
//
// For now this stub just returns the input content so the pipeline compiles.
async function runLocalModelForTask(
  _task: Classification,
  input: { content?: string; platform?: string; context?: unknown },
): Promise<string> {
  // Placeholder: echo content or a very simple fallback.
  if (input.content && input.content.trim().length > 0) {
    return input.content;
  }

  // Minimal safe default if no content is provided.
  return "Placeholder content generated by badgr_pipeline (TODO: wire into ollama_generate).";
}

// ----------------- Tool Registration -----------------

export function registerBadgrPipelineTools(server: McpServer) {
  // 1) badgr_classify
  const classifyTool: Tool = {
    name: "badgr_classify",
    description:
      "Classify a social/profile request into task_type, complexity, requires_rag, and domain.",
    inputSchema: BadgrClassifyInputSchema,
    outputSchema: ClassificationSchema,
    async handler(input) {
      const parsed = BadgrClassifyInputSchema.parse(input);
      const classification = classifyText(parsed.request);
      return classification;
    },
  };

  // 2) badgr_execute
  const executeTool: Tool = {
    name: "badgr_execute",
    description:
      "Execute a social/profile task using local models with guards and cascading.",
    inputSchema: BadgrExecuteInputSchema,
    outputSchema: BadgrPipelineOutputSchema,
    async handler(input) {
      const parsed = BadgrExecuteInputSchema.parse(input);
      const { classification, content, platform, context } = parsed;

      const route = routingTable[classification.task_type];
      if (!route) {
        const fallback: BadgrPipelineOutput = {
          c: "",
          s: { routing: 0 },
          v: ["unknown_task_type"],
          r: false,
          conf: 0,
          err: ["routing_failed"],
          needs_claude_review: true,
        };
        return fallback;
      }

      // ---- Primary attempt with the main local model ----
      const firstContent = await runLocalModelForTask(classification, {
        content,
        platform,
        context,
      });
      const firstGuard = basicGuard(firstContent);

      if (firstGuard.output.r && firstGuard.output.conf >= 0.7) {
        return firstGuard.output;
      }

      // ---- Fallback to bigger local model if configured ----
      if (route.fallbackModel) {
        const secondContent = await runLocalModelForTask(classification, {
          content,
          platform,
          context,
        });
        const secondGuard = basicGuard(secondContent);
        if (secondGuard.output.r && secondGuard.output.conf >= 0.75) {
          return secondGuard.output;
        }
      }

      // ---- Still not good: flag for Claude review ----
      const flagged = firstGuard.output;
      flagged.needs_claude_review = true;
      return flagged;
    },
  };

  server.registerTool(classifyTool);
  server.registerTool(executeTool);
}
2. Wire it into your existing MCP server (src/index.ts)
In your current src/index.ts (where you initialize McpServer and register tools), add:

ts
// src/index.ts (excerpt)

import { McpServer } from "@modelcontextprotocol/sdk/server";
// ...other imports...
import { registerBadgrPipelineTools } from "./badgr_pipeline";

async function main() {
  const server = new McpServer({
    // existing server options...
  });

  // register existing Ollama tools here (list, run, chat_completion, etc.)

  // Register BADGR social-profile pipeline tools
  registerBadgrPipelineTools(server);

  // start stdio transport or whatever you already do
  // ...
}

main().catch((err) => {
  console.error("MCP server failed to start:", err);
  process.exit(1);
});
This makes two new tools visible to Claude:

badgr_classify

badgr_execute

which match the behavior in your CLAUDE.md and the control sheet.

<END>
And Lastly:
==============\/

What still needs wiring (but is now clearly marked)
To “boil the ocean” fully:

Replace the runLocalModelForTask stub with real calls to your existing tools defined in social-profile-tools.json (e.g. ollama_generate, ollama_validate).

Extend basicGuard to:

enforce TikTok char limits and other platform constraints from your JSON config,

optionally call a validator tool if you want LLM-based checks.

Optionally move the routing table into config so you can tweak models without code changes.

Once you plug those in, you have:

A real badgr_pipeline tool pair in MCP,

A Claude workspace spec that tells Claude to use them correctly,

A prompt cheatsheet that keeps your inputs short and on‑pattern,

And a path for tightening routing/guards over time without changing the core architecture.

* Also read the 'README-stack-ops.md' at '/home/t0n34781/dev/claude-mcp-stack/' when all is checke dout and ready here. Confirm once reviewed.

<END>

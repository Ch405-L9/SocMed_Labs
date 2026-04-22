==============================================================================
==============================================================================
badgr_pipeline.ts
==============================================================================
==============================================================================

// src/badgr_pipeline.ts
// BADGRTech social-profile pipeline — two MCP tools: badgr_classify + badgr_execute
// Stages: CLASSIFIER → ROUTER → EXECUTION (cascade) → GUARD → COMPACT OUTPUT
// Token-efficient: scoped system prompts, needs_claude_review gate, {c,s,v,r,conf,err} output

import { z } from "zod";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { Ollama } from "ollama";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { queryRag } from "./rag.js";

// ── Ollama client ─────────────────────────────────────────────────────────────
const OLLAMA_HOST = process.env.OLLAMA_HOST ?? "http://127.0.0.1:11434";
const ollama = new Ollama({ host: OLLAMA_HOST });

// ── Load char limits from social-profile-tools.json ──────────────────────────
// Single source of truth — avoids duplicating limits in multiple places.
// build/badgr_pipeline.js → ../social-profile-tools.json resolves to project root.
const __filename = fileURLToPath(import.meta.url);
const __dirname  = dirname(__filename);

let charLimits: Record<string, Record<string, number>>;
try {
  const raw = JSON.parse(
    readFileSync(join(__dirname, "../social-profile-tools.json"), "utf8"),
  ) as Array<Record<string, unknown>>;
  const profileBuild = raw.find(t => t["name"] === "ollama_profile_build") as
    | { inputSchema?: { platform_field_limits?: Record<string, Record<string, number>> } }
    | undefined;
  charLimits = profileBuild?.inputSchema?.platform_field_limits ?? {};
} catch {
  // Inline fallback — mirrors social-profile-tools.json values
  charLimits = {
    tiktok:    { bio: 80,   display_name: 30  },
    x:         { bio: 160,  display_name: 50  },
    youtube:   { description: 1000, display_name: 100 },
    instagram: { bio: 150,  display_name: 30  },
    facebook:  { about: 255, display_name: 75 },
    linkedin:  { headline: 220, about: 2600, display_name: 100 },
  };
}


// ── Types & Zod Schemas ───────────────────────────────────────────────────────

export const TaskTypeEnum = z.enum([
  "small_edit",
  "generation",
  "profile_setup",
  "asset_pipeline",
  "analysis",
]);
export type TaskType = z.infer<typeof TaskTypeEnum>;

export const ComplexityEnum  = z.enum(["low", "medium", "high"]);
export const DomainEnum      = z.enum(["social"]);

export const ClassificationSchema = z.object({
  task_type:    TaskTypeEnum,
  complexity:   ComplexityEnum,
  requires_rag: z.boolean(),
  domain:       DomainEnum,
});
export type Classification = z.infer<typeof ClassificationSchema>;

// Compact output schema — every field maps to a short key to minimise token use
export const BadgrOutputSchema = z.object({
  c:                   z.string(),                                       // content
  s:                   z.record(z.string(), z.number().min(0).max(100)), // per-check scores
  v:                   z.array(z.string()),                              // violation codes
  r:                   z.boolean(),                                      // ready_for_use
  conf:                z.number().min(0).max(1),                         // confidence 0–1
  err:                 z.array(z.string()),                              // errors / auto-resolutions
  needs_claude_review: z.boolean(),
});
export type BadgrOutput = z.infer<typeof BadgrOutputSchema>;


// ── Routing Table ─────────────────────────────────────────────────────────────
// primary → first attempt.  fallback → cascade if confidence < 0.7 or error.
// Mirrors badgr_brand_rules.model_routing — do not change without updating SYSTEM_CHANGELOG.md.
const ROUTING: Record<TaskType, { primary: string; fallback?: string; timeoutMs: number }> = {
  small_edit:     { primary: "llama3.2:3b",    fallback: "gemma3:4b",    timeoutMs: 10_000 },
  generation:     { primary: "gemma3:4b",       fallback: "llama3.1:8b", timeoutMs: 30_000 },
  profile_setup:  { primary: "gemma3:4b",       fallback: "llama3.1:8b", timeoutMs: 45_000 },
  asset_pipeline: { primary: "gemma3:4b",                                timeoutMs: 20_000 },
  analysis:       { primary: "mistral:latest",                           timeoutMs: 45_000 },
};

// Primary profile field per platform — used when field_type is not specified
const PRIMARY_FIELD: Record<string, string> = {
  tiktok:    "bio",
  x:         "bio",
  youtube:   "description",
  instagram: "bio",
  facebook:  "about",
  linkedin:  "headline",
};

// Platform-registered handles
const HANDLES: Record<string, string> = {
  tiktok:    "@badgrtech25",
  x:         "@badgrtechnologies",
  instagram: "@badgrtechnologies",
  youtube:   "@badgrtechnologies",
  facebook:  "@badgrtechnologies",
  linkedin:  "@badgrtechnologies",
};

// Guard constants
const FORBIDDEN_NAMES = [
  "BADGR Technologies", "Badgr Tech", "badgr tech", "BADGR TECH", "Badgr Technologies",
];
const FLUFF = [
  "welcome to", "hey guys", "today we", "as a leading provider",
  "join the revolution", "unlock your", "dramatically improve",
  "stop losing", "introducing", "did you know",
];
const ALLOWED_DOLLARS    = new Set(["$197", "$500"]);
const BIO_Q_EXCEPTIONS   = new Set(["tiktok"]);


// ── System Prompts ────────────────────────────────────────────────────────────
// Scoped per task type. Smaller tasks get smaller prompts — direct token saving.

const FULL_PROMPT = `You generate content for BADGRTechnologies LLC (brand: BADGRTech).
MANDATORY RULES:
- Brand name: "BADGRTech" or "BADGRTechnologies LLC". Never: "BADGR Technologies", "Badgr Tech", "BADGR TECH".
- No emojis. No question openers in posts/captions. No fluff phrases.
- No fabricated stats. Allowed only: "$197–$500", "14 days", "15-min audit", "results vary".
- ICP: ATL Metro law firms (5–25 person) and medical/dental practices only.
- Service: 14-Day Lead Leak & Compliance Fix. Free 15-min audit — ATL only.
- Tagline: CTRL+ALT+DELIVER.
- Plain text output only — no markdown, no [H1] tags.`;

const EDIT_PROMPT =
  `Edit content for BADGRTech. No emojis. Brand name: "BADGRTech". Return only the edited text, nothing else.`;

const ASSET_PROMPT =
  `Generate an ImageMagick command for a BADGRTech profile image. ` +
  `Background: #0E305F. Source: official_badgr-logo_px512.png (never modify the original). ` +
  `Return the command string only.`;

const ANALYSIS_PROMPT =
  `Analyze a BADGRTech social profile. ` +
  `ICP: ATL law firms + medical/dental. Offer: 14-Day Lead Leak & Compliance Fix, $197–$500. ` +
  `Return a prioritised fix list of up to 5 items. Plain text, no markdown.`;

function buildSystemPrompt(taskType: TaskType, platform?: string, fieldType?: string): string {
  switch (taskType) {
    case "small_edit":     return EDIT_PROMPT;
    case "asset_pipeline": return ASSET_PROMPT;
    case "analysis":       return ANALYSIS_PROMPT;
    default: {
      const handle   = HANDLES[platform ?? ""] ?? "@badgrtechnologies";
      const limit    = platform && fieldType ? charLimits[platform]?.[fieldType] : undefined;
      const limitStr = limit ? `\nField: ${platform} ${fieldType}. Hard limit: ${limit} chars.` : "";
      return `${FULL_PROMPT}\nCTA handle: ${handle}.${limitStr}`;
    }
  }
}

function buildUserPrompt(
  taskType:  TaskType,
  platform:  string | undefined,
  content:   string | undefined,
  fieldType: string | undefined,
  context:   string | undefined,
): string {
  const pf       = platform  ?? "general";
  const ft       = fieldType ?? PRIMARY_FIELD[platform ?? ""] ?? "bio";
  const limit    = platform  ? (charLimits[platform]?.[ft] ?? 0) : 0;
  const nameLimit = platform ? (charLimits[platform]?.["display_name"] ?? 30) : 30;

  const parts: string[] = [];

  switch (taskType) {
    case "small_edit":
      parts.push(`Edit the following ${pf} ${ft}:\n"${content ?? ""}"`);
      if (context) parts.push(`Change: ${context}`);
      if (limit)   parts.push(`Keep under ${limit} chars.`);
      parts.push("Return only the edited text.");
      break;

    case "profile_setup":
      parts.push(
        `Generate a complete ${pf} profile for BADGRTech as JSON with these exact keys:`,
        `{ "name": "<≤${nameLimit} chars>",`,
        `  "bio": "<≤${limit || 80} chars, pattern: pain→outcome→CTA>",`,
        `  "hashtags": ["<5 discovery tags>", "<2 branded tags>"],`,
        `  "link_strategy": "<bio link recommendation>" }`,
      );
      if (content) parts.push(`Context: ${content}`);
      if (context) parts.push(context);
      break;

    case "generation":
      parts.push(`Generate a ${pf} ${ft} for BADGRTech.`);
      if (limit)   parts.push(`Max ${limit} chars.`);
      if (content) parts.push(`Existing context: ${content}`);
      if (context) parts.push(context);
      break;

    case "asset_pipeline":
      parts.push(`Generate ImageMagick command for ${pf} profile photo.`);
      if (context) parts.push(context);
      break;

    case "analysis":
      parts.push(`Analyse this ${pf} profile for BADGRTech:`);
      parts.push(content ?? "(no content provided)");
      if (context) parts.push(`Additional context: ${context}`);
      parts.push("Return: top 5 fixes, one sentence each.");
      break;
  }

  return parts.join("\n");
}


// ── Execution Helpers ─────────────────────────────────────────────────────────

function withTimeout<T>(p: Promise<T>, ms: number): Promise<T> {
  return Promise.race([
    p,
    new Promise<never>((_, rej) =>
      setTimeout(() => rej(new Error(`timeout after ${ms}ms`)), ms),
    ),
  ]);
}

async function callOllama(
  model:     string,
  system:    string,
  user:      string,
  timeoutMs: number,
): Promise<{ content: string; error?: string }> {
  try {
    const res = await withTimeout(
      ollama.chat({
        model,
        messages: [
          { role: "system", content: system },
          { role: "user",   content: user   },
        ],
        options: { temperature: 0.3 },
      }),
      timeoutMs,
    );
    return { content: res.message.content };
  } catch (e) {
    return { content: "", error: e instanceof Error ? e.message : String(e) };
  }
}


// ── Guard ─────────────────────────────────────────────────────────────────────
// G1 emojis (auto-strip) · G2 forbidden names · G3 question opener
// G4 char limit · G5 % stats · G6 $ amounts · G7 fluff phrases
// asset_pipeline and analysis skip brand-voice checks — not copy outputs.

interface GuardResult {
  content:       string;
  scores:        Record<string, number>;
  violations:    string[];
  auto_resolved: string[];
  ready:         boolean;
  confidence:    number;
}

function runGuard(
  raw:      string,
  platform: string,
  ft:       string,
  taskType: TaskType,
): GuardResult {
  const brandVoice = taskType !== "asset_pipeline" && taskType !== "analysis";
  let   content    = raw.trim();
  const violations:    string[] = [];
  const auto_resolved: string[] = [];
  const scores: Record<string, number> = {};

  // G1 — emoji (auto-strip)
  const emojiRx = /[\u{1F000}-\u{1FFFF}]|[\u{2600}-\u{27BF}]|[︀-️]/gu;
  if (emojiRx.test(content)) {
    content = content.replace(emojiRx, "").replace(/[ \t]{2,}/g, " ").trim();
    auto_resolved.push("emoji_stripped");
    scores["emoji"] = 70;
  } else {
    scores["emoji"] = 100;
  }

  if (brandVoice) {
    // G2 — forbidden name forms
    let namePen = 0;
    for (const f of FORBIDDEN_NAMES) {
      if (content.includes(f)) {
        violations.push(`forbidden_name:${f.replace(/ /g, "_")}`);
        namePen += 20;
      }
    }
    scores["brand_name"] = Math.max(0, 100 - namePen);

    // G3 — question opener
    // Exception: TikTok bio — question opener is an intentional conversion hook
    const isBioQ = ["bio","about","description","headline"].includes(ft) && BIO_Q_EXCEPTIONS.has(platform);
    if (!isBioQ && /^[^.!]*\?/.test(content.split(/\n/)[0].trim())) {
      violations.push("question_opener");
      scores["voice"] = 55;
    } else {
      scores["voice"] = 100;
    }

    // G5 — percentage stats (all fabricated until real client data exists)
    const pcts = [...content.matchAll(/\d+\s*%/g)].map(m => m[0]);
    if (pcts.length > 0) {
      violations.push(`fabricated_stat:${pcts.join(",")}`);
      scores["stats"] = 40;
    } else {
      scores["stats"] = 100;
    }

    // G6 — out-of-range dollar amounts
    const dollars     = [...content.matchAll(/\$(\d[\d,]*)/g)].map(m => m[0]);
    const badDollars  = dollars.filter(d => !ALLOWED_DOLLARS.has(d));
    if (badDollars.length > 0) {
      violations.push(`suspicious_dollar:${badDollars.join(",")}`);
      scores["stats"] = Math.min(scores["stats"] ?? 100, 40);
    }

    // G7 — fluff phrases
    const lower    = content.toLowerCase();
    const fluffHit = FLUFF.filter(p => lower.includes(p));
    if (fluffHit.length > 0) {
      violations.push(`fluff:${fluffHit.join("|")}`);
      scores["copy"] = Math.max(0, 100 - fluffHit.length * 10);
    } else {
      scores["copy"] = 100;
    }
  } else {
    scores["brand_name"] = 100;
    scores["voice"]      = 100;
    scores["stats"]      = 100;
    scores["copy"]       = 100;
  }

  // G4 — char limit (applies to all task types)
  const limit = charLimits[platform]?.[ft];
  if (limit !== undefined) {
    if (content.length > limit) {
      violations.push(`char_overflow:${content.length}>${limit}`);
      scores["char_limit"] = Math.max(0, Math.round((limit / content.length) * 100));
    } else {
      scores["char_limit"] = 100;
    }
  } else {
    scores["char_limit"] = 100;
  }

  const vals       = Object.values(scores);
  const confidence = vals.length > 0 ? vals.reduce((a, b) => a + b, 0) / vals.length / 100 : 0.5;

  return { content, scores, violations, auto_resolved, ready: violations.length === 0, confidence };
}


// ── Classifier ────────────────────────────────────────────────────────────────
// Rule-based, zero Ollama calls — instant and token-free.

function classify(request: string): Classification {
  const lo = request.toLowerCase();

  const editW  = +/\b(tweak|edit|fix|change|update|adjust|revise|modify|swap)\b/.test(lo) * 3
               + +/\b(small|minor|quick|just)\b/.test(lo) * 2;
  const genW   = +/\b(generate|create|write|draft|new|make)\b/.test(lo) * 3
               + +/\b(bio|caption|hashtag|hook|cta|tagline)\b/.test(lo) * 2;
  const setupW = +/\b(profile|setup|build|complete|full)\b/.test(lo) * 3
               + +/\b(name|handle|link|strategy)\b/.test(lo) * 2;
  const assetW = +/\b(image|photo|logo|banner|cover|avatar|resize|convert|imagemagick|px)\b/.test(lo) * 3;
  const anlsW  = +/\b(audit|analyz|diagnose|review|teardown|fix.?list|what.?wrong)\b/.test(lo) * 3;

  const scores: Record<TaskType, number> = {
    small_edit:     editW,
    generation:     genW,
    profile_setup:  setupW,
    asset_pipeline: assetW,
    analysis:       anlsW,
  };

  let best: TaskType = "generation";
  let bestScore = -1;
  for (const [t, s] of Object.entries(scores) as [TaskType, number][]) {
    if (s > bestScore) { bestScore = s; best = t; }
  }

  const words    = request.split(/\s+/).length;
  const platforms = (lo.match(/tiktok|instagram|youtube|facebook|twitter|\bx\b|linkedin/g) ?? []).length;
  const complexity: "low" | "medium" | "high" =
    words < 10 && platforms <= 1 ? "low"
    : words > 30 || platforms > 1 ? "high"
    : "medium";

  // RAG is needed when the request explicitly invokes the viral tech video knowledge base
  const RAG_TRIGGERS = /viral.?tech.?video|use.*video.?system|use.*video.?pattern|use.*video.?doc|video.?strategy|from.?knowledge.?base|use.?rag/i;
  const requires_rag = RAG_TRIGGERS.test(request);

  return { task_type: best, complexity, requires_rag, domain: "social" };
}


// ── Execute pipeline ──────────────────────────────────────────────────────────

async function execute(input: {
  classification: Classification;
  content?:       string;
  platform?:      string;
  field_type?:    string;
  context?:       string;
}): Promise<BadgrOutput> {
  const { classification, content, platform, context } = input;
  const tt    = classification.task_type;
  const route = ROUTING[tt];
  const ft    = input.field_type ?? (platform ? PRIMARY_FIELD[platform] : undefined) ?? "bio";

  // ── RAG context injection ─────────────────────────────────────────────
  // When requires_rag is true, retrieve the most relevant viral-tech-video
  // knowledge chunks and prepend them to the system prompt so the model
  // grounds its response in the indexed knowledge base.
  let system = buildSystemPrompt(tt, platform, ft);

  if (classification.requires_rag) {
    try {
      const ragQuery = `viral tech video system context: ${content ?? ""} ${context ?? ""}`.trim();
      const chunks   = await queryRag(ollama, ragQuery, 4);
      if (chunks.length > 0) {
        const ragBlock = chunks.map(c => c.text).join("\n\n---\n\n");
        system += `\n\nVIRAL TECH VIDEO KNOWLEDGE BASE (retrieved context):\n\n${ragBlock}`;
      }
    } catch {
      // Index not built or embed model unavailable — proceed without RAG
    }
  }

  const userMsg = buildUserPrompt(tt, platform, content, ft, context);

  // ── Primary attempt ──────────────────────────────────────────────
  const first = await callOllama(route.primary, system, userMsg, route.timeoutMs);

  if (first.error) {
    if (route.fallback) {
      const fb = await callOllama(route.fallback, system, userMsg, route.timeoutMs);
      if (fb.error) {
        return errorOutput(["ollama_unavailable", first.error, fb.error]);
      }
      return toOutput(runGuard(fb.content, platform ?? "generic", ft, tt));
    }
    return errorOutput(["ollama_unavailable", first.error]);
  }

  const g1 = runGuard(first.content, platform ?? "generic", ft, tt);

  // ── Cascade: try fallback if low confidence ───────────────────────
  if (g1.confidence < 0.7 && route.fallback) {
    const fb = await callOllama(route.fallback, system, userMsg, route.timeoutMs);
    if (!fb.error) {
      const g2 = runGuard(fb.content, platform ?? "generic", ft, tt);
      if (g2.confidence > g1.confidence) {
        return toOutput(g2);
      }
    }
  }

  return toOutput(g1);
}

function toOutput(g: GuardResult): BadgrOutput {
  return {
    c:                   g.content,
    s:                   g.scores,
    v:                   g.violations,
    r:                   g.ready,
    conf:                parseFloat(g.confidence.toFixed(3)),
    err:                 g.auto_resolved,
    needs_claude_review: !g.ready || g.confidence < 0.7,
  };
}

function errorOutput(errs: string[]): BadgrOutput {
  return { c: "", s: {}, v: [], r: false, conf: 0, err: errs, needs_claude_review: true };
}


// ── Tool Registration ─────────────────────────────────────────────────────────

export function registerBadgrPipelineTools(server: McpServer): void {
  // ── badgr_classify ────────────────────────────────────────────────
  // Zero Ollama calls. Always call this first — costs nothing.
  server.registerTool(
    "badgr_classify",
    {
      title: "BADGR Classify",
      description:
        "Classify a social profile task into task_type, complexity, requires_rag, domain. " +
        "Rule-based — no model call, instant. " +
        "Always run before badgr_execute. Use result to decide escalation path.",
      inputSchema: {
        request: z.string().describe("Raw user request or task description"),
      },
    },
    async ({ request }) => ({
      content: [{ type: "text", text: JSON.stringify(classify(request), null, 2) }],
    }),
  );

  // ── badgr_execute ─────────────────────────────────────────────────
  // Full pipeline. Returns compact output — Claude reads only when needs_claude_review = true.
  server.registerTool(
    "badgr_execute",
    {
      title: "BADGR Execute",
      description:
        "Run a social profile task through the full pipeline: route → local model → guard → compact output. " +
        "Cascades to a larger model if confidence < 0.7. " +
        "Output keys: c (content), s (scores), v (violations), r (ready), conf (0–1), err (errors/auto-fixes), needs_claude_review. " +
        "If r=true and needs_claude_review=false: content is ready, skim and pass. " +
        "If needs_claude_review=true: fix violations in v before surfacing.",
      inputSchema: {
        classification: z.object({
          task_type:    TaskTypeEnum,
          complexity:   ComplexityEnum,
          requires_rag: z.boolean(),
          domain:       DomainEnum,
        }).describe("Output from badgr_classify"),
        content:    z.string().optional().describe("Existing bio, content, or material to work from"),
        platform:   z.enum(["tiktok","x","youtube","instagram","facebook","linkedin"]).optional(),
        field_type: z.enum(["bio","about","description","display_name","caption","headline","post"]).optional(),
        context:    z.string().optional().describe("Edit instructions or additional task context"),
      },
    },
    async ({ classification, content, platform, field_type, context }) => ({
      content: [
        {
          type: "text",
          text: JSON.stringify(
            await execute({ classification, content, platform, field_type, context }),
            null,
            2,
          ),
        },
      ],
    }),
  );
}

==============================================================================
==============================================================================
index.ts
==============================================================================
==============================================================================

#!/usr/bin/env node
// Modern MCP Server API for Ollama MCP (stdio transport only, HTTP/SSE planned for future)
//
// Future: Add HTTP/SSE transports for remote multi-client access (see memory bank).
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { ContentBlock } from "@modelcontextprotocol/sdk/types.js";
import { Ollama } from "ollama";
import { readFileSync } from "node:fs";
import { z } from "zod";
import { registerBadgrPipelineTools } from "./badgr_pipeline.js";
import { buildIndex, queryRag, indexExists, EMBED_MODEL, INDEX_PATH } from "./rag.js";


// Default Ollama API endpoint
const OLLAMA_HOST = process.env.OLLAMA_HOST || "http://127.0.0.1:11434";
const ollama = new Ollama({ host: OLLAMA_HOST });

// Helper for error formatting
const formatError = (error: unknown): string =>
  error instanceof Error ? error.message : String(error);

const pkg = JSON.parse(readFileSync(new URL("../package.json", import.meta.url), "utf8"));

const server = new McpServer({
  name: "ollama-mcp-server",
  version: pkg.version,
});


// ============================================================
// BADGR CONTENT PIPELINE
// REQUEST → CLASSIFIER → ROUTER → TOOL EXECUTION → GUARD → OUTPUT
// ============================================================

// --- Pipeline Types ---
type TaskType = "copy_gen" | "summarization" | "code_and_structured_data" | "routing_utility";

// --- Model Routing Map ---
// Source of truth: badgr_brand_rules.model_routing in social-profile-tools.json
// NEVER override without updating SYSTEM_CHANGELOG.md
const MODEL_ROUTING: Record<TaskType | "fallback", string> = {
  copy_gen:                 "gemma3:4b",       // mistral:latest EXCLUDED — fails structured gen
  summarization:            "mistral:latest",
  code_and_structured_data: "qwen2.5-coder:7b",
  routing_utility:          "llama3.2:3b",
  fallback:                 "gemma3:4b",
};

// --- Platform Character Limits ---
const CHAR_LIMITS: Record<string, Record<string, number>> = {
  tiktok:    { bio: 80,   display_name: 30 },
  x:         { bio: 160,  display_name: 50 },
  youtube:   { description: 1000, display_name: 100 },
  instagram: { bio: 150,  display_name: 30 },
  facebook:  { about: 255, display_name: 75 },
  linkedin:  { headline: 220, about: 2600, display_name: 100 },
};

// --- Guard Constants ---
const FORBIDDEN_NAME_FORMS = [
  "BADGR Technologies",
  "Badgr Tech",
  "badgr tech",
  "BADGR TECH",
  "Badgr Technologies",
];

const FLUFF_PHRASES = [
  "welcome to",
  "hey guys",
  "today we",
  "as a leading provider",
  "join the revolution",
  "unlock your",
  "dramatically improve",
  "stop losing",
  "introducing",
  "did you know",
];

// Dollar amounts the brand uses legitimately — all others are suspicious
const ALLOWED_DOLLAR_AMOUNTS = new Set(["$197", "$500"]);

// Platforms where a question opener in a BIO field is an intentional exception
const BIO_QUESTION_OPENER_EXCEPTIONS = new Set(["tiktok"]);

// Platform handles per registration
const PLATFORM_HANDLES: Record<string, string> = {
  tiktok:    "@badgrtech25",
  x:         "@badgrtechnologies",
  instagram: "@badgrtechnologies",
  youtube:   "@badgrtechnologies",
  facebook:  "@badgrtechnologies",
  linkedin:  "@badgrtechnologies",
};

// --- Brand System Prompt (injected at TOOL EXECUTION stage) ---
const BADGR_SYSTEM_PROMPT = `You generate content for BADGRTechnologies LLC (brand: BADGRTech).

MANDATORY RULES — any violation fails review:
- Brand name: "BADGRTech" (display) or "BADGRTechnologies LLC" (legal). NEVER: "BADGR Technologies", "Badgr Tech", "BADGR TECH".
- No emojis of any kind.
- No question openers in posts or captions. Lead with a statement.
- No fabricated statistics. Only permitted: "$197–$500", "14 days", "15-min audit", "results vary".
- No fluff: "welcome to", "hey guys", "today we", "as a leading provider", "join the revolution", "stop losing", "introducing".
- ICP: ATL Metro law firms (5–25 person) and medical/dental practices ONLY.
- Service: 14-Day Lead Leak & Compliance Fix. Free 15-min audit — ATL businesses only.
- Tagline: CTRL+ALT+DELIVER.
- Output plain text only. No markdown, no [H1] tags, no bullet symbols beyond → arrows.`;


// ============================================================
// STAGE 1: CLASSIFIER
// Maps the incoming task_type to an internal TaskType category.
// ============================================================
function classify(
  task_type_input: string,
  platform?: string,
): { task_type: TaskType; platform: string | undefined } {
  const COPY_GEN_TYPES    = new Set(["write", "rewrite", "profile_bio", "profile_build", "brainstorm", "expand"]);
  const SUMMARY_TYPES     = new Set(["summarize"]);
  const CODE_TYPES        = new Set(["format", "code", "structured"]);
  const ROUTING_TYPES     = new Set(["classify", "route", "triage"]);

  let task_type: TaskType;
  if (COPY_GEN_TYPES.has(task_type_input))    task_type = "copy_gen";
  else if (SUMMARY_TYPES.has(task_type_input)) task_type = "summarization";
  else if (CODE_TYPES.has(task_type_input))    task_type = "code_and_structured_data";
  else if (ROUTING_TYPES.has(task_type_input)) task_type = "routing_utility";
  else                                          task_type = "copy_gen";

  return { task_type, platform };
}


// ============================================================
// STAGE 2: ROUTER — HARD RULES
// Routes to correct model. No overrides without brand rule update.
// ============================================================
function route(task_type: TaskType): { model: string; reason: string } {
  const model = MODEL_ROUTING[task_type] ?? MODEL_ROUTING.fallback;

  const REASONS: Record<TaskType, string> = {
    copy_gen:
      "gemma3:4b — structured copy generation. mistral:latest EXCLUDED: known failure mode (echoes instructions verbatim on profile_build tasks, confirmed 2026-04-20).",
    summarization:
      "mistral:latest — long-form context compression (7.2B).",
    code_and_structured_data:
      "qwen2.5-coder:7b — code and structured data tasks.",
    routing_utility:
      "llama3.2:3b — lightweight fast classification (3B).",
  };

  return { model, reason: REASONS[task_type] ?? `${MODEL_ROUTING.fallback} (fallback)` };
}


// ============================================================
// STAGE 3: TOOL EXECUTION
// Calls Ollama with brand system prompt injected.
// ============================================================
async function executeWithBrandContext(
  model: string,
  userPrompt: string,
  platform?: string,
  fieldType?: string,
  constraints?: string,
  additionalContext?: string,
): Promise<string> {
  const handle = platform ? PLATFORM_HANDLES[platform] : "@badgrtechnologies";

  const systemParts = [
    BADGR_SYSTEM_PROMPT,
    platform
      ? `Platform: ${platform}. Field: ${fieldType ?? "post"}. CTA handle: ${handle}.`
      : "",
    constraints  ? `Constraints: ${constraints}`         : "",
    additionalContext ? `Context: ${additionalContext}` : "",
  ].filter(Boolean);

  const response = await ollama.chat({
    model,
    messages: [
      { role: "system", content: systemParts.join("\n\n") },
      { role: "user",   content: userPrompt },
    ],
    options: { temperature: 0.3 },
  });

  return response.message.content;
}


// ============================================================
// STAGE 4: GUARD — LIMITS
// Post-generation validation. Auto-sanitizes emojis.
// All other violations require human review before output use.
// ============================================================
function guard(
  content: string,
  platform: string,
  fieldType: string,
): {
  pass: boolean;
  violations: string[];
  auto_resolved: string[];
  sanitized_content: string;
  brand_alignment_score: number;
  compliance_score: number;
  copy_quality_score: number;
} {
  const violations: string[] = [];
  const auto_resolved: string[] = [];
  let sanitized = content;
  let brandScore    = 100;
  let compliScore   = 100;
  let copyScore     = 100;

  // G1 — Emoji detection + auto-strip
  const emojiRx = /[\u{1F000}-\u{1FFFF}]|[\u{2600}-\u{27BF}]|[\uFE00-\uFE0F]/gu;
  if (emojiRx.test(content)) {
    sanitized = sanitized
      .replace(/[\u{1F000}-\u{1FFFF}]|[\u{2600}-\u{27BF}]|[\uFE00-\uFE0F]/gu, "")
      .replace(/[ \t]{2,}/g, " ")
      .trim();
    auto_resolved.push("EMOJI: Emojis detected and stripped automatically.");
    brandScore -= 10;
  }

  // G2 — Forbidden name forms
  for (const forbidden of FORBIDDEN_NAME_FORMS) {
    if (content.includes(forbidden)) {
      violations.push(
        `BRAND_NAME: Forbidden form "${forbidden}" — replace with "BADGRTech" (display) or "BADGRTechnologies LLC" (legal).`
      );
      brandScore -= 20;
    }
  }

  // G3 — Question opener
  // Exception: TikTok bio field allows question opener (intentional conversion hook)
  const isBioField = ["bio", "about", "description", "headline"].includes(fieldType);
  const isTikTokBioException = isBioField && BIO_QUESTION_OPENER_EXCEPTIONS.has(platform);
  if (!isTikTokBioException) {
    const firstLine = content.split(/\n/)[0].trim();
    if (/^[^.!]*\?/.test(firstLine)) {
      violations.push(
        `QUESTION_OPENER: Content opens with a question. Rewrite as statement-first.`
      );
      brandScore -= 15;
      copyScore  -= 20;
    }
  }

  // G4 — Character limit
  const platformLimits = CHAR_LIMITS[platform];
  if (platformLimits) {
    const limit = platformLimits[fieldType];
    if (limit !== undefined && sanitized.length > limit) {
      violations.push(
        `CHAR_LIMIT: ${sanitized.length} chars — exceeds ${platform} ${fieldType} limit of ${limit}. Trim required.`
      );
      compliScore -= 30;
    }
  }

  // G5 — Fabricated percentage stats
  const percentMatches = [...sanitized.matchAll(/\d+\s*%/g)].map(m => m[0]);
  if (percentMatches.length > 0) {
    violations.push(
      `STATS_REVIEW: Percentage stat(s) found: ${percentMatches.join(", ")} — no verified client data exists. Replace with "results vary" or process-proof language.`
    );
    brandScore -= 25;
  }

  // G6 — Fabricated or out-of-range dollar amounts
  const dollarMatches = [...sanitized.matchAll(/\$(\d[\d,]*)/g)].map(m => m[0]);
  const suspiciousDollars = dollarMatches.filter(m => !ALLOWED_DOLLAR_AMOUNTS.has(m));
  if (suspiciousDollars.length > 0) {
    violations.push(
      `STATS_REVIEW: Dollar amount(s) outside $197–$500 range: ${suspiciousDollars.join(", ")} — verify source or replace.`
    );
    brandScore -= 25;
  }

  // G7 — Fluff phrases
  const contentLower = sanitized.toLowerCase();
  for (const phrase of FLUFF_PHRASES) {
    if (contentLower.includes(phrase)) {
      violations.push(`FLUFF: Phrase "${phrase}" detected — rewrite.`);
      copyScore -= 10;
    }
  }

  return {
    pass: violations.length === 0,
    violations,
    auto_resolved,
    sanitized_content: sanitized,
    brand_alignment_score: Math.max(0, brandScore),
    compliance_score:      Math.max(0, compliScore),
    copy_quality_score:    Math.max(0, copyScore),
  };
}


// ============================================================
// EXISTING TOOLS — Ollama model management
// ============================================================

// Tool: List models
server.registerTool(
  "list",
  {
    title: "List models",
    description: "List all models in Ollama",
    inputSchema: {},
  },
  async () => {
    try {
      const result = await ollama.list();
      return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
    } catch (error) {
      return { content: [{ type: "text", text: `Error: ${formatError(error)}` }], isError: true };
    }
  }
);

// Tool: Show model info
server.registerTool(
  "show",
  {
    title: "Show model info",
    description: "Show information for a model",
    inputSchema: { name: z.string() },
  },
  async ({ name }) => {
    try {
      const result = await ollama.show({ model: name });
      return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
    } catch (error) {
      return { content: [{ type: "text", text: `Error: ${formatError(error)}` }], isError: true };
    }
  }
);

// Tool: Create model (remote only supports 'from')
server.registerTool(
  "create",
  {
    title: "Create model (remote only supports 'from')",
    description: "Create a model from a base model (remote only, no Modelfile support)",
    inputSchema: { name: z.string(), from: z.string() },
  },
  async ({ name, from }) => {
    try {
      const result = await ollama.create({ model: name, from });
      return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
    } catch (error) {
      return { content: [{ type: "text", text: `Error: ${formatError(error)}` }], isError: true };
    }
  }
);

// Tool: Pull model
server.registerTool(
  "pull",
  {
    title: "Pull model",
    description: "Pull a model from a registry",
    inputSchema: { name: z.string() },
  },
  async ({ name }) => {
    try {
      const result = await ollama.pull({ model: name });
      return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
    } catch (error) {
      return { content: [{ type: "text", text: `Error: ${formatError(error)}` }], isError: true };
    }
  }
);

// Tool: Push model
server.registerTool(
  "push",
  {
    title: "Push model",
    description: "Push a model to a registry",
    inputSchema: { name: z.string() },
  },
  async ({ name }) => {
    try {
      const result = await ollama.push({ model: name });
      return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
    } catch (error) {
      return { content: [{ type: "text", text: `Error: ${formatError(error)}` }], isError: true };
    }
  }
);

// Tool: Copy model
server.registerTool(
  "cp",
  {
    title: "Copy model",
    description: "Copy a model",
    inputSchema: { source: z.string(), destination: z.string() },
  },
  async ({ source, destination }) => {
    try {
      const result = await ollama.copy({ source, destination });
      return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
    } catch (error) {
      return { content: [{ type: "text", text: `Error: ${formatError(error)}` }], isError: true };
    }
  }
);

// Tool: Remove model
server.registerTool(
  "rm",
  {
    title: "Remove model",
    description: "Remove a model",
    inputSchema: { name: z.string() },
  },
  async ({ name }) => {
    try {
      const result = await ollama.delete({ model: name });
      return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
    } catch (error) {
      return { content: [{ type: "text", text: `Error: ${formatError(error)}` }], isError: true };
    }
  }
);

 // Tool: Run model (non-streaming)
server.registerTool(
  "run",
  {
    title: "Run model",
    description: "Run a model with a prompt. Optionally accepts an image file path for vision/multimodal models and a temperature parameter.",
    inputSchema: {
      name: z.string(),
      prompt: z.string(),
      images: z.array(z.string()).optional(), // Array of image paths
      temperature: z.number().min(0).max(2).optional(),
      think: z.boolean().optional(),
    },
  },
  async ({ name, prompt, images, temperature, think }) => {
    try {
      const result = await ollama.generate({
        model: name,
        prompt,
        options: temperature !== undefined ? { temperature } : {},
        ...(images ? { images } : {}),
        ...(think !== undefined ? { think } : {}),
      });

      const content: Array<ContentBlock> = [];
      if (result?.thinking) {
        content.push({ type: "text", text: `<think>${result.thinking}</think>` });
      }
      content.push({ type: "text", text: result.response ?? "" });
      return { content };
    } catch (error) {
      return { content: [{ type: "text", text: `Error: ${formatError(error)}` }], isError: true };
    }
  }
);

// Tool: Chat completion (OpenAI-compatible)
server.registerTool(
  "chat_completion",
  {
    title: "Chat completion",
    description: "OpenAI-compatible chat completion API. Supports optional images per message for vision/multimodal models.",
    inputSchema: {
      model: z.string(),
      messages: z.array(z.object({
        role: z.enum(["system", "user", "assistant"]),
        content: z.string(),
        images: z.array(z.string()).optional(), // Array of image paths
      })),
      temperature: z.number().min(0).max(2).optional(),
      think: z.boolean().optional(),
    },
  },
  async ({ model, messages, temperature, think }) => {
    try {
      const response = await ollama.chat({
        model,
        messages,
        options: { temperature },
        ...(think !== undefined ? { think } : {}),
      });
      return {
        content: [
          {
            type: "text",
            text: JSON.stringify({
              id: "chatcmpl-" + Date.now(),
              object: "chat.completion",
              created: Math.floor(Date.now() / 1000),
              model,
              choices: [
                {
                  index: 0,
                  message: response.message,
                  finish_reason: "stop",
                },
              ],
            }, null, 2),
          },
        ],
      };
    } catch (error) {
      return { content: [{ type: "text", text: `Error: ${formatError(error)}` }], isError: true };
    }
  }
);


// ============================================================
// TOOL: badgr_pipeline
// REQUEST → CLASSIFIER → ROUTER → TOOL EXECUTION → GUARD → OUTPUT
//
// Single entry point for all brand-aware content generation.
// Enforces model routing, injects brand context, validates output.
// Use this instead of calling run/chat_completion directly for any
// BADGRTech content task.
// ============================================================
server.registerTool(
  "badgr_pipeline",
  {
    title: "BADGR Content Pipeline",
    description: [
      "Full content generation pipeline with brand enforcement.",
      "Stages: REQUEST → CLASSIFIER → ROUTER → TOOL EXECUTION → GUARD → OUTPUT.",
      "Automatically routes to the correct model per brand rules,",
      "injects the BADGR brand system prompt, and validates output against",
      "all brand guardrails before returning. Use for all BADGRTech content tasks.",
    ].join(" "),
    inputSchema: {
      task_type: z.enum([
        "write",
        "rewrite",
        "summarize",
        "profile_bio",
        "profile_build",
        "brainstorm",
        "format",
        "expand",
        "classify",
      ]).describe("Type of task — determines model routing and guard behavior"),

      input: z.string()
        .describe("The prompt, content to rewrite, or task description"),

      platform: z.enum([
        "tiktok", "x", "youtube", "instagram", "facebook", "linkedin",
      ]).optional()
        .describe("Target platform — sets char limits, handle, and link rules for guard checks"),

      field_type: z.enum([
        "bio", "about", "description", "display_name",
        "caption", "headline", "post",
      ]).optional()
        .describe("Platform field being generated — used for char limit validation"),

      constraints: z.string().optional()
        .describe("Additional hard constraints, e.g. 'under 80 chars', 'statement-first, no price mention'"),

      additional_context: z.string().optional()
        .describe("Extra context beyond brand rules, e.g. specific client scenario or post angle"),
    },
  },
  async ({ task_type, input, platform, field_type, constraints, additional_context }) => {
    const startTime = Date.now();
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const trace: Record<string, any> = {};

    try {
      // ── STAGE 1: CLASSIFIER ───────────────────────────────
      const classification = classify(task_type, platform);
      trace.stage_1_classifier = {
        input_task_type: task_type,
        resolved_task_type: classification.task_type,
        platform: classification.platform ?? "not specified",
      };

      // ── STAGE 2: ROUTER ───────────────────────────────────
      const routing = route(classification.task_type);
      trace.stage_2_router = {
        model: routing.model,
        reason: routing.reason,
      };

      // ── STAGE 3: TOOL EXECUTION ───────────────────────────
      const rawOutput = await executeWithBrandContext(
        routing.model,
        input,
        platform,
        field_type,
        constraints,
        additional_context,
      );
      trace.stage_3_execution = {
        model_used:        routing.model,
        raw_output_chars:  rawOutput.length,
        platform_handle:   platform ? PLATFORM_HANDLES[platform] : "not specified",
      };

      // ── STAGE 4: GUARD ────────────────────────────────────
      const guardResult = guard(
        rawOutput,
        platform ?? "generic",
        field_type ?? "post",
      );
      trace.stage_4_guard = {
        pass:                 guardResult.pass,
        violations_count:     guardResult.violations.length,
        auto_resolved_count:  guardResult.auto_resolved.length,
        brand_alignment_score: guardResult.brand_alignment_score,
        compliance_score:      guardResult.compliance_score,
        copy_quality_score:    guardResult.copy_quality_score,
      };

      // ── STAGE 5: OUTPUT ───────────────────────────────────
      const output = {
        content:          guardResult.sanitized_content,
        char_count:       guardResult.sanitized_content.length,
        ready_for_use:    guardResult.pass,
        auto_resolved:    guardResult.auto_resolved,
        violations:       guardResult.violations,
        requires_review:  !guardResult.pass,
        scores: {
          brand_alignment: guardResult.brand_alignment_score,
          compliance:      guardResult.compliance_score,
          copy_quality:    guardResult.copy_quality_score,
        },
      };

      const result = {
        pipeline_result: {
          ...trace,
          stage_5_output:   output,
          run_duration_ms:  Date.now() - startTime,
        },
      };

      return {
        content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
      };

    } catch (error) {
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            pipeline_error: {
              message:        formatError(error),
              trace_at_error: trace,
              run_duration_ms: Date.now() - startTime,
            },
          }, null, 2),
        }],
        isError: true,
      };
    }
  }
);


// ============================================================
// TOOL: ollama_rag_build
// One-time (or on-change) indexer for rag_sources/*.md.
// Embeds all chunks via OLLAMA_EMBED_MODEL (default: nomic-embed-text)
// and writes rag_index_viral_videos.json to the project root.
// Must be run before ollama_rag_query will return results.
// ============================================================
server.registerTool(
  "ollama_rag_build",
  {
    title: "Build RAG Index",
    description: [
      "Index all knowledge-base files in rag_sources/ into rag_index_viral_videos.json.",
      "Must be called once (or after rag_sources files change) before ollama_rag_query works.",
      `Embedding model: ${EMBED_MODEL} (override with OLLAMA_EMBED_MODEL env var).`,
      `Index output: ${INDEX_PATH}`,
    ].join(" "),
    inputSchema: {},
  },
  async () => {
    try {
      const result = await buildIndex(ollama);
      return {
        content: [{
          type: "text",
          text: JSON.stringify({ status: "ok", ...result }, null, 2),
        }],
      };
    } catch (error) {
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            status: "error",
            message: formatError(error),
            hint: `Make sure '${EMBED_MODEL}' is pulled in Ollama, or set OLLAMA_EMBED_MODEL to an available model.`,
          }, null, 2),
        }],
        isError: true,
      };
    }
  },
);


// ============================================================
// TOOL: ollama_rag_query
// Semantic search over the indexed viral tech video knowledge base.
// Returns top-k chunks by cosine similarity to the query.
// Requires rag_index_viral_videos.json — run ollama_rag_build first.
// ============================================================
server.registerTool(
  "ollama_rag_query",
  {
    title: "RAG Query",
    description: [
      "Query the local viral tech video knowledge base using semantic similarity.",
      "Returns top-k chunks from rag_index_viral_videos.json.",
      "Run ollama_rag_build first if index does not exist.",
      "Used automatically by badgr_execute when requires_rag=true.",
    ].join(" "),
    inputSchema: {
      query:   z.string().describe("Search query — what context to retrieve"),
      top_k:   z.number().int().min(1).max(20).optional()
                .describe("Number of chunks to return (default: 5)"),
      filters: z.record(z.string()).optional()
                .describe("Optional key/value filters, e.g. { tags: 'platform_strategy,viral_tech_2026' }"),
    },
  },
  async ({ query, top_k, filters }) => {
    try {
      if (!indexExists()) {
        return {
          content: [{
            type: "text",
            text: JSON.stringify({
              status: "no_index",
              message: "RAG index not found. Call ollama_rag_build to create it.",
              index_path: INDEX_PATH,
            }, null, 2),
          }],
          isError: true,
        };
      }

      const results = await queryRag(ollama, query, top_k ?? 5, filters ?? {});
      return {
        content: [{
          type: "text",
          text: JSON.stringify({ status: "ok", query, results }, null, 2),
        }],
      };
    } catch (error) {
      return {
        content: [{
          type: "text",
          text: JSON.stringify({ status: "error", message: formatError(error) }, null, 2),
        }],
        isError: true,
      };
    }
  },
);


// BADGR social-profile pipeline: badgr_classify + badgr_execute
registerBadgrPipelineTools(server);

// Start stdio transport (future: add HTTP/SSE)
const transport = new StdioServerTransport();
await server.connect(transport);

==============================================================================
==============================================================================
rag.ts
==============================================================================
==============================================================================


// src/rag.ts
// Local RAG module for the BADGR viral-tech-video knowledge base.
// Two public operations:
//   buildIndex(ollama) — chunk rag_sources/*.md, embed, write rag_index_viral_videos.json
//   queryRag(ollama, query, topK, filters) — embed query, cosine search, return top-k chunks

import { Ollama } from "ollama";
import {
  readFileSync, writeFileSync, existsSync, readdirSync,
} from "node:fs";
import { join, basename } from "node:path";
import { fileURLToPath } from "node:url";
import { dirname } from "node:path";

const __filename     = fileURLToPath(import.meta.url);
const __dirname      = dirname(__filename);
const PROJECT_ROOT   = join(__dirname, "..");

export const RAG_SOURCES_DIR = join(PROJECT_ROOT, "rag_sources");
export const INDEX_PATH      = join(PROJECT_ROOT, "rag_index_viral_videos.json");
export const EMBED_MODEL     = process.env.OLLAMA_EMBED_MODEL ?? "nomic-embed-text";

// rag_setup_instructions_viral_videos.md is meta — not knowledge to be indexed
const SKIP_FILES = new Set(["rag_setup_instructions_viral_videos.md"]);

// ── Types ──────────────────────────────────────────────────────────────────────

export interface RagChunk {
  id:     string;
  source: string;
  text:   string;
  tags:   string[];
  vector: number[];
}

interface RagIndex {
  built_at:    string;
  embed_model: string;
  chunks:      RagChunk[];
}

export interface RagResult {
  id:     string;
  source: string;
  text:   string;
  tags:   string[];
  score:  number;
}


// ── Chunking ───────────────────────────────────────────────────────────────────

// Split general markdown files into sections at ## headings
function chunkByHeadings(text: string, source: string): Array<{ text: string; tags: string[] }> {
  const parts  = text.split(/^## /m);
  const chunks: Array<{ text: string; tags: string[] }> = [];

  for (const part of parts) {
    const trimmed = part.trim();
    if (trimmed.length < 50) continue;
    const heading = trimmed.split("\n")[0].trim();
    chunks.push({
      text: `## ${trimmed}`,
      tags: [source, heading.toLowerCase().replace(/\W+/g, "_").slice(0, 48)],
    });
  }
  return chunks;
}

// Parse "## Chunk: <id>" blocks separated by --- in viral_tech_video_chunks_charts.md
function chunkByChunkBlocks(text: string): Array<{ text: string; tags: string[] }> {
  const blocks  = text.split(/\n---\n/).filter(b => b.includes("**Text:**"));
  const results: Array<{ text: string; tags: string[] }> = [];

  for (const block of blocks) {
    const idMatch   = block.match(/##\s+Chunk:\s*(\S+)/);
    const tagsMatch = block.match(/\*\*Tags:\*\*\s*([^\n]+)/);
    const textMatch = block.match(/\*\*Text:\*\*\s*([\s\S]+)/);
    if (!idMatch || !textMatch) continue;

    const id       = idMatch[1];
    const tags     = tagsMatch
      ? tagsMatch[1].split(",").map(t => t.trim()).filter(Boolean)
      : [id];
    const bodyText = textMatch[1].trim();

    results.push({ text: `[chunk:${id}] ${bodyText}`, tags });
  }
  return results;
}


// ── Math ───────────────────────────────────────────────────────────────────────

function cosineSim(a: number[], b: number[]): number {
  if (a.length === 0 || b.length === 0) return 0;
  let dot = 0, na = 0, nb = 0;
  for (let i = 0; i < a.length; i++) {
    dot += a[i] * b[i];
    na  += a[i] * a[i];
    nb  += b[i] * b[i];
  }
  return na === 0 || nb === 0 ? 0 : dot / (Math.sqrt(na) * Math.sqrt(nb));
}


// ── Index build ────────────────────────────────────────────────────────────────

export async function buildIndex(
  ollama: Ollama,
): Promise<{ chunks_indexed: number; embed_model: string; index_path: string }> {
  const files = readdirSync(RAG_SOURCES_DIR)
    .filter(f => f.endsWith(".md") && !SKIP_FILES.has(f))
    .sort();

  if (files.length === 0) {
    throw new Error(`No indexable .md files found in ${RAG_SOURCES_DIR}`);
  }

  const raw: Array<{ text: string; tags: string[]; source: string }> = [];

  for (const file of files) {
    const content = readFileSync(join(RAG_SOURCES_DIR, file), "utf8");
    const source  = basename(file, ".md");

    if (file === "viral_tech_video_chunks_charts.md") {
      // Pre-chunked file: parse Chunk blocks directly
      for (const c of chunkByChunkBlocks(content)) {
        raw.push({ ...c, source });
      }
    } else {
      // General markdown: split by ## headings
      for (const c of chunkByHeadings(content, source)) {
        raw.push({ ...c, source });
      }
    }
  }

  const chunks: RagChunk[] = [];
  for (let i = 0; i < raw.length; i++) {
    const rc  = raw[i];
    const res = await ollama.embed({ model: EMBED_MODEL, input: rc.text });
    const vec: number[] = Array.isArray(res.embeddings?.[0])
      ? (res.embeddings[0] as number[])
      : [];
    chunks.push({
      id:     `chunk_${i}`,
      source: rc.source,
      text:   rc.text,
      tags:   rc.tags,
      vector: vec,
    });
  }

  const index: RagIndex = {
    built_at:    new Date().toISOString(),
    embed_model: EMBED_MODEL,
    chunks,
  };

  writeFileSync(INDEX_PATH, JSON.stringify(index), "utf8");
  invalidateCache();

  return { chunks_indexed: chunks.length, embed_model: EMBED_MODEL, index_path: INDEX_PATH };
}


// ── Query ──────────────────────────────────────────────────────────────────────

let _cache: RagIndex | null = null;
function invalidateCache(): void { _cache = null; }

function loadIndex(): RagIndex | null {
  if (_cache) return _cache;
  if (!existsSync(INDEX_PATH)) return null;
  try {
    _cache = JSON.parse(readFileSync(INDEX_PATH, "utf8")) as RagIndex;
    return _cache;
  } catch {
    return null;
  }
}

export function indexExists(): boolean {
  return existsSync(INDEX_PATH);
}

export async function queryRag(
  ollama:  Ollama,
  query:   string,
  topK    = 5,
  filters: Record<string, string> = {},
): Promise<RagResult[]> {
  const index = loadIndex();
  if (!index) return [];

  const res  = await ollama.embed({ model: index.embed_model, input: query });
  const qvec: number[] = Array.isArray(res.embeddings?.[0])
    ? (res.embeddings[0] as number[])
    : [];
  if (qvec.length === 0) return [];

  let candidates = index.chunks;

  if (filters["tags"]) {
    const tagSet = new Set(filters["tags"].split(",").map(t => t.trim()));
    candidates = candidates.filter(c => c.tags.some(t => tagSet.has(t)));
  }

  return candidates
    .map(c => ({
      id:    c.id,
      source: c.source,
      text:  c.text,
      tags:  c.tags,
      score: cosineSim(qvec, c.vector),
    }))
    .sort((a, b) => b.score - a.score)
    .slice(0, topK);
}

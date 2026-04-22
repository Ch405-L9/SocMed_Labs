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

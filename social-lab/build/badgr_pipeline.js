// src/badgr_pipeline.ts
// BADGRTech social-profile pipeline — two MCP tools: badgr_classify + badgr_execute
// Stages: CLASSIFIER → ROUTER → EXECUTION (cascade) → GUARD → COMPACT OUTPUT
// Token-efficient: scoped system prompts, needs_claude_review gate, {c,s,v,r,conf,err} output
import { z } from "zod";
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
const __dirname = dirname(__filename);
let charLimits;
try {
    const raw = JSON.parse(readFileSync(join(__dirname, "../social-profile-tools.json"), "utf8"));
    const profileBuild = raw.find(t => t["name"] === "ollama_profile_build");
    charLimits = profileBuild?.inputSchema?.platform_field_limits ?? {};
}
catch {
    // Inline fallback — mirrors social-profile-tools.json values
    charLimits = {
        tiktok: { bio: 80, display_name: 30 },
        x: { bio: 160, display_name: 50 },
        youtube: { description: 1000, display_name: 100 },
        instagram: { bio: 150, display_name: 30 },
        facebook: { about: 255, display_name: 75 },
        linkedin: { headline: 220, about: 2600, display_name: 100 },
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
export const ComplexityEnum = z.enum(["low", "medium", "high"]);
export const DomainEnum = z.enum(["social"]);
export const ClassificationSchema = z.object({
    task_type: TaskTypeEnum,
    complexity: ComplexityEnum,
    requires_rag: z.boolean(),
    domain: DomainEnum,
});
// Compact output schema — every field maps to a short key to minimise token use
export const BadgrOutputSchema = z.object({
    c: z.string(), // content
    s: z.record(z.string(), z.number().min(0).max(100)), // per-check scores
    v: z.array(z.string()), // violation codes
    r: z.boolean(), // ready_for_use
    conf: z.number().min(0).max(1), // confidence 0–1
    err: z.array(z.string()), // errors / auto-resolutions
    needs_claude_review: z.boolean(),
});
// ── Routing Table ─────────────────────────────────────────────────────────────
// primary → first attempt.  fallback → cascade if confidence < 0.7 or error.
// Mirrors badgr_brand_rules.model_routing — do not change without updating SYSTEM_CHANGELOG.md.
const ROUTING = {
    small_edit: { primary: "llama3.2:3b", fallback: "gemma3:4b", timeoutMs: 10_000 },
    generation: { primary: "gemma3:4b", fallback: "llama3.1:8b", timeoutMs: 30_000 },
    profile_setup: { primary: "gemma3:4b", fallback: "llama3.1:8b", timeoutMs: 45_000 },
    asset_pipeline: { primary: "gemma3:4b", timeoutMs: 20_000 },
    analysis: { primary: "mistral:latest", timeoutMs: 45_000 },
};
// Primary profile field per platform — used when field_type is not specified
const PRIMARY_FIELD = {
    tiktok: "bio",
    x: "bio",
    youtube: "description",
    instagram: "bio",
    facebook: "about",
    linkedin: "headline",
};
// Platform-registered handles
const HANDLES = {
    tiktok: "@badgrtech25",
    x: "@badgrtechnologies",
    instagram: "@badgrtechnologies",
    youtube: "@badgrtechnologies",
    facebook: "@badgrtechnologies",
    linkedin: "@badgrtechnologies",
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
const ALLOWED_DOLLARS = new Set(["$197", "$500"]);
const BIO_Q_EXCEPTIONS = new Set(["tiktok"]);
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
const EDIT_PROMPT = `Edit content for BADGRTech. No emojis. Brand name: "BADGRTech". Return only the edited text, nothing else.`;
const ASSET_PROMPT = `Generate an ImageMagick command for a BADGRTech profile image. ` +
    `Background: #0E305F. Source: official_badgr-logo_px512.png (never modify the original). ` +
    `Return the command string only.`;
const ANALYSIS_PROMPT = `Analyze a BADGRTech social profile. ` +
    `ICP: ATL law firms + medical/dental. Offer: 14-Day Lead Leak & Compliance Fix, $197–$500. ` +
    `Return a prioritised fix list of up to 5 items. Plain text, no markdown.`;
function buildSystemPrompt(taskType, platform, fieldType) {
    switch (taskType) {
        case "small_edit": return EDIT_PROMPT;
        case "asset_pipeline": return ASSET_PROMPT;
        case "analysis": return ANALYSIS_PROMPT;
        default: {
            const handle = HANDLES[platform ?? ""] ?? "@badgrtechnologies";
            const limit = platform && fieldType ? charLimits[platform]?.[fieldType] : undefined;
            const limitStr = limit ? `\nField: ${platform} ${fieldType}. Hard limit: ${limit} chars.` : "";
            return `${FULL_PROMPT}\nCTA handle: ${handle}.${limitStr}`;
        }
    }
}
function buildUserPrompt(taskType, platform, content, fieldType, context) {
    const pf = platform ?? "general";
    const ft = fieldType ?? PRIMARY_FIELD[platform ?? ""] ?? "bio";
    const limit = platform ? (charLimits[platform]?.[ft] ?? 0) : 0;
    const nameLimit = platform ? (charLimits[platform]?.["display_name"] ?? 30) : 30;
    const parts = [];
    switch (taskType) {
        case "small_edit":
            parts.push(`Edit the following ${pf} ${ft}:\n"${content ?? ""}"`);
            if (context)
                parts.push(`Change: ${context}`);
            if (limit)
                parts.push(`Keep under ${limit} chars.`);
            parts.push("Return only the edited text.");
            break;
        case "profile_setup":
            parts.push(`Generate a complete ${pf} profile for BADGRTech as JSON with these exact keys:`, `{ "name": "<≤${nameLimit} chars>",`, `  "bio": "<≤${limit || 80} chars, pattern: pain→outcome→CTA>",`, `  "hashtags": ["<5 discovery tags>", "<2 branded tags>"],`, `  "link_strategy": "<bio link recommendation>" }`);
            if (content)
                parts.push(`Context: ${content}`);
            if (context)
                parts.push(context);
            break;
        case "generation":
            parts.push(`Generate a ${pf} ${ft} for BADGRTech.`);
            if (limit)
                parts.push(`Max ${limit} chars.`);
            if (content)
                parts.push(`Existing context: ${content}`);
            if (context)
                parts.push(context);
            break;
        case "asset_pipeline":
            parts.push(`Generate ImageMagick command for ${pf} profile photo.`);
            if (context)
                parts.push(context);
            break;
        case "analysis":
            parts.push(`Analyse this ${pf} profile for BADGRTech:`);
            parts.push(content ?? "(no content provided)");
            if (context)
                parts.push(`Additional context: ${context}`);
            parts.push("Return: top 5 fixes, one sentence each.");
            break;
    }
    return parts.join("\n");
}
// ── Execution Helpers ─────────────────────────────────────────────────────────
function withTimeout(p, ms) {
    return Promise.race([
        p,
        new Promise((_, rej) => setTimeout(() => rej(new Error(`timeout after ${ms}ms`)), ms)),
    ]);
}
async function callOllama(model, system, user, timeoutMs) {
    try {
        const res = await withTimeout(ollama.chat({
            model,
            messages: [
                { role: "system", content: system },
                { role: "user", content: user },
            ],
            options: { temperature: 0.3 },
        }), timeoutMs);
        return { content: res.message.content };
    }
    catch (e) {
        return { content: "", error: e instanceof Error ? e.message : String(e) };
    }
}
function runGuard(raw, platform, ft, taskType) {
    const brandVoice = taskType !== "asset_pipeline" && taskType !== "analysis";
    let content = raw.trim();
    const violations = [];
    const auto_resolved = [];
    const scores = {};
    // G1 — emoji (auto-strip)
    const emojiRx = /[\u{1F000}-\u{1FFFF}]|[\u{2600}-\u{27BF}]|[︀-️]/gu;
    if (emojiRx.test(content)) {
        content = content.replace(emojiRx, "").replace(/[ \t]{2,}/g, " ").trim();
        auto_resolved.push("emoji_stripped");
        scores["emoji"] = 70;
    }
    else {
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
        const isBioQ = ["bio", "about", "description", "headline"].includes(ft) && BIO_Q_EXCEPTIONS.has(platform);
        if (!isBioQ && /^[^.!]*\?/.test(content.split(/\n/)[0].trim())) {
            violations.push("question_opener");
            scores["voice"] = 55;
        }
        else {
            scores["voice"] = 100;
        }
        // G5 — percentage stats (all fabricated until real client data exists)
        const pcts = [...content.matchAll(/\d+\s*%/g)].map(m => m[0]);
        if (pcts.length > 0) {
            violations.push(`fabricated_stat:${pcts.join(",")}`);
            scores["stats"] = 40;
        }
        else {
            scores["stats"] = 100;
        }
        // G6 — out-of-range dollar amounts
        const dollars = [...content.matchAll(/\$(\d[\d,]*)/g)].map(m => m[0]);
        const badDollars = dollars.filter(d => !ALLOWED_DOLLARS.has(d));
        if (badDollars.length > 0) {
            violations.push(`suspicious_dollar:${badDollars.join(",")}`);
            scores["stats"] = Math.min(scores["stats"] ?? 100, 40);
        }
        // G7 — fluff phrases
        const lower = content.toLowerCase();
        const fluffHit = FLUFF.filter(p => lower.includes(p));
        if (fluffHit.length > 0) {
            violations.push(`fluff:${fluffHit.join("|")}`);
            scores["copy"] = Math.max(0, 100 - fluffHit.length * 10);
        }
        else {
            scores["copy"] = 100;
        }
    }
    else {
        scores["brand_name"] = 100;
        scores["voice"] = 100;
        scores["stats"] = 100;
        scores["copy"] = 100;
    }
    // G4 — char limit (applies to all task types)
    const limit = charLimits[platform]?.[ft];
    if (limit !== undefined) {
        if (content.length > limit) {
            violations.push(`char_overflow:${content.length}>${limit}`);
            scores["char_limit"] = Math.max(0, Math.round((limit / content.length) * 100));
        }
        else {
            scores["char_limit"] = 100;
        }
    }
    else {
        scores["char_limit"] = 100;
    }
    const vals = Object.values(scores);
    const confidence = vals.length > 0 ? vals.reduce((a, b) => a + b, 0) / vals.length / 100 : 0.5;
    return { content, scores, violations, auto_resolved, ready: violations.length === 0, confidence };
}
// ── Classifier ────────────────────────────────────────────────────────────────
// Rule-based, zero Ollama calls — instant and token-free.
function classify(request) {
    const lo = request.toLowerCase();
    const editW = +/\b(tweak|edit|fix|change|update|adjust|revise|modify|swap)\b/.test(lo) * 3
        + +/\b(small|minor|quick|just)\b/.test(lo) * 2;
    const genW = +/\b(generate|create|write|draft|new|make)\b/.test(lo) * 3
        + +/\b(bio|caption|hashtag|hook|cta|tagline)\b/.test(lo) * 2;
    const setupW = +/\b(profile|setup|build|complete|full)\b/.test(lo) * 3
        + +/\b(name|handle|link|strategy)\b/.test(lo) * 2;
    const assetW = +/\b(image|photo|logo|banner|cover|avatar|resize|convert|imagemagick|px)\b/.test(lo) * 3;
    const anlsW = +/\b(audit|analyz|diagnose|review|teardown|fix.?list|what.?wrong)\b/.test(lo) * 3;
    const scores = {
        small_edit: editW,
        generation: genW,
        profile_setup: setupW,
        asset_pipeline: assetW,
        analysis: anlsW,
    };
    let best = "generation";
    let bestScore = -1;
    for (const [t, s] of Object.entries(scores)) {
        if (s > bestScore) {
            bestScore = s;
            best = t;
        }
    }
    const words = request.split(/\s+/).length;
    const platforms = (lo.match(/tiktok|instagram|youtube|facebook|twitter|\bx\b|linkedin/g) ?? []).length;
    const complexity = words < 10 && platforms <= 1 ? "low"
        : words > 30 || platforms > 1 ? "high"
            : "medium";
    // RAG is needed when the request explicitly invokes the viral tech video knowledge base
    const RAG_TRIGGERS = /viral.?tech.?video|use.*video.?system|use.*video.?pattern|use.*video.?doc|video.?strategy|from.?knowledge.?base|use.?rag/i;
    const requires_rag = RAG_TRIGGERS.test(request);
    return { task_type: best, complexity, requires_rag, domain: "social" };
}
// ── Execute pipeline ──────────────────────────────────────────────────────────
async function execute(input) {
    const { classification, content, platform, context } = input;
    const tt = classification.task_type;
    const route = ROUTING[tt];
    const ft = input.field_type ?? (platform ? PRIMARY_FIELD[platform] : undefined) ?? "bio";
    // ── RAG context injection ─────────────────────────────────────────────
    // When requires_rag is true, retrieve the most relevant viral-tech-video
    // knowledge chunks and prepend them to the system prompt so the model
    // grounds its response in the indexed knowledge base.
    let system = buildSystemPrompt(tt, platform, ft);
    if (classification.requires_rag) {
        try {
            const ragQuery = `viral tech video system context: ${content ?? ""} ${context ?? ""}`.trim();
            const chunks = await queryRag(ollama, ragQuery, 4);
            if (chunks.length > 0) {
                const ragBlock = chunks.map(c => c.text).join("\n\n---\n\n");
                system += `\n\nVIRAL TECH VIDEO KNOWLEDGE BASE (retrieved context):\n\n${ragBlock}`;
            }
        }
        catch {
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
function toOutput(g) {
    return {
        c: g.content,
        s: g.scores,
        v: g.violations,
        r: g.ready,
        conf: parseFloat(g.confidence.toFixed(3)),
        err: g.auto_resolved,
        needs_claude_review: !g.ready || g.confidence < 0.7,
    };
}
function errorOutput(errs) {
    return { c: "", s: {}, v: [], r: false, conf: 0, err: errs, needs_claude_review: true };
}
// ── Tool Registration ─────────────────────────────────────────────────────────
export function registerBadgrPipelineTools(server) {
    // ── badgr_classify ────────────────────────────────────────────────
    // Zero Ollama calls. Always call this first — costs nothing.
    server.registerTool("badgr_classify", {
        title: "BADGR Classify",
        description: "Classify a social profile task into task_type, complexity, requires_rag, domain. " +
            "Rule-based — no model call, instant. " +
            "Always run before badgr_execute. Use result to decide escalation path.",
        inputSchema: {
            request: z.string().describe("Raw user request or task description"),
        },
    }, async ({ request }) => ({
        content: [{ type: "text", text: JSON.stringify(classify(request), null, 2) }],
    }));
    // ── badgr_execute ─────────────────────────────────────────────────
    // Full pipeline. Returns compact output — Claude reads only when needs_claude_review = true.
    server.registerTool("badgr_execute", {
        title: "BADGR Execute",
        description: "Run a social profile task through the full pipeline: route → local model → guard → compact output. " +
            "Cascades to a larger model if confidence < 0.7. " +
            "Output keys: c (content), s (scores), v (violations), r (ready), conf (0–1), err (errors/auto-fixes), needs_claude_review. " +
            "If r=true and needs_claude_review=false: content is ready, skim and pass. " +
            "If needs_claude_review=true: fix violations in v before surfacing.",
        inputSchema: {
            classification: z.object({
                task_type: TaskTypeEnum,
                complexity: ComplexityEnum,
                requires_rag: z.boolean(),
                domain: DomainEnum,
            }).describe("Output from badgr_classify"),
            content: z.string().optional().describe("Existing bio, content, or material to work from"),
            platform: z.enum(["tiktok", "x", "youtube", "instagram", "facebook", "linkedin"]).optional(),
            field_type: z.enum(["bio", "about", "description", "display_name", "caption", "headline", "post"]).optional(),
            context: z.string().optional().describe("Edit instructions or additional task context"),
        },
    }, async ({ classification, content, platform, field_type, context }) => ({
        content: [
            {
                type: "text",
                text: JSON.stringify(await execute({ classification, content, platform, field_type, context }), null, 2),
            },
        ],
    }));
}

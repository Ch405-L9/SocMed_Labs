# BADGRTech – Claude + MCP + Ollama Control Sheet

> Standard: **Boil the ocean.**  
> Complete, production-grade, token-efficient, local-first by default.

---

## 0. Core Principles

- **Local-first, cascade, Claude-as-architect**
  - Bulk work → local models via MCP.
  - Claude → planning, architecture, review, edge cases.
- **Hard routing, not vibes**
  - Every request is classified, then routed by rules.
  - No direct model picking by Claude; MCP decides.
- **Boil the ocean**
  - Aim for finished artifacts (code + tests + minimal docs), not plans.
  - Prefer smaller scope fully done over bigger scope half-done.
- **Token discipline**
  - Minimal context, compact tool IO, no unnecessary schemas.
  - Cloud reasoning only when needed or explicitly requested.

---

## 1. Pre‑Project Setup (Do Once Per Machine/Stack)

### 1.1 Tools and Servers

- Ensure installed:
  - Node.js + npm
  - Ollama (with your models pulled)
  - MCP servers:
    - `ollama-mcp-server` (generic Ollama bridge)[file:41]
    - filesystem MCP (root: `/home/.../projects`)[file:38]
    - memory MCP (global memory JSON)[file:38]

- Confirm Ollama models:
  - `gemma3:4b` – copy
  - `mistral:latest` – summarize / compress
  - `qwen2.5-coder:7b` – code / tests
  - `llama3.2:3b` / `phi3:mini` – routing / classification
  - `llama3.1:8b` – harder local tasks

### 1.2 Global MCP Config (`~/.claude.json`)

- Map MCP servers to commands (Ollama MCP, filesystem, memory).[file:38]
- Keep this small and stable; it’s your **global wiring**.

### 1.3 Memory Bank & Product Docs

- Ensure these exist and are up to date:[file:44][file:45][file:48][file:49]
  - `memory-bank/systemPatterns.md` – architecture, “Boil the ocean” full text.
  - `memory-bank/productContext.md` – why this stack exists.
  - `memory-bank/techContext.md` – tech stack and constraints.
  - `memory-bank/activeContext.md` / `progress.md` – current status and decisions.

You **do not** paste these into each prompt; Claude references them when needed.

---

## 2. Project‑Level Setup (Per Repo / Workspace)

### 2.1 CLAUDE.md (Behavior Contract)

- Put a `CLAUDE.md` at the project root with:
  - Roles:
    - Claude = architect + reviewer.
    - MCP `badgr_pipeline` = classifier + router + guard + cascade.
    - Local models = executors (copy, summarize, code).
  - Mandatory classification:
    - “Always call `badgr_pipeline.classify()` first.”
  - Routing:
    - `task_type` → small_edit / generation / research / build / analysis / profile_setup / asset_pipeline.
    - “Do not pick models directly; trust `badgr_pipeline`.”
  - Cascade handling:
    - Use `needs_claude_review`, `conf`, `err` to decide when to patch vs ship.
  - Boil the ocean rules (compressed):
    - Full execution when feasible.
    - Code + tests + minimal docs for meaningful changes.
    - Ask 1–2 clarifying questions only when critical; then proceed.

(You can use the full CLAUDE.md I wrote earlier as your base and refine from there.)

### 2.2 Platform / Domain Specs

- For social/profile work: maintain `social-profile-tools.json`.[file:40]
  - Contains:
    - `ollama_generate`, `ollama_validate`, `ollama_rag_query`, etc.
    - Platform limits (e.g., TikTok bio 80 chars, platform enums).
    - Brand context paths, character limits, failure modes.
- For image/profile standards, encode as JSON:
  - `profile_image_standard` (TikTok):
    - `canvas_px`: 720
    - `safe_zone_pct`: 0.8–0.85
    - `shape`: `square_input_circle_display`
    - `background_hex`: `#0E305F`
    - `text_allowed`: false
  - This lets tools generate proper ImageMagick commands without re-deriving logic.

---

## 3. MCP Control Plane: `badgr_pipeline` (Core Logic)

> This is the “brains” between Claude and Ollama. Build it once; reuse everywhere.

### 3.1 Stages

1. **CLASSIFIER – `classify()`**
   - Input: raw user request (or Claude’s task summary).
   - Output:
     ```json
     {
       "task_type": "small_edit | generation | research | build | analysis | profile_setup | asset_pipeline",
       "complexity": "low | medium | high",
       "requires_rag": true | false,
       "domain": "social | web_app | api | infra | other"
     }
     ```

2. **ROUTER – `route()`**
   - Uses routing table to select:
     - local model(s),
     - whether RAG is allowed,
     - expansion guard limits (tokens, tools, steps).

3. **EXECUTION – `execute()`**
   - Calls underlying Ollama MCP tools:
     - `ollama_generate`, `ollama_extract`, `ollama_rag_query`, etc.[file:40]
   - Injects:
     - brand context path,
     - platform constraints,
     - any relevant file snippets.

4. **GUARD – `guard()`**
   - Applies:
     - emoji detection/strip, forbidden names, char limits, fluff checks, numeric sanity.
   - For code tasks:
     - optionally runs tests/build and tags errors.

5. **CASCADE – `cascade()`**
   - Pattern:
     - small/cheap model attempt → guard → confidence.
     - if low `conf` or errors → fallback to bigger local model.
     - if still shaky → set `needs_claude_review = true`.

6. **RESPOND – `respond()`**
   - Output (compact JSON):
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

### 3.2 Routing Rules (Conceptual Table)

- `small_edit` → Gemma 3 4B, no RAG, tight token & step limits.
- `generation` → Gemma 3 4B → fallback Llama 3.1 8B.
- `build` → Qwen coder 7B → fallback Llama 3.1 8B.
- `analysis` → Mistral (summaries/compression).
- `research` → cloud reasoning (Claude) + RAG tools.
- `profile_setup` / `asset_pipeline` → Gemma 3 4B / Mistral, using `social-profile-tools.json`.

---

## 4. Claude’s Behavior (Per Request)

### 4.1 Always First: Classification

- On any user task:
  1. Call `badgr_pipeline.classify()` with the raw request.
  2. Wait for classification; do **not** call other tools first.

### 4.2 Then: Execute via MCP

- Call `badgr_pipeline.execute()` with:
  - classification result,
  - any necessary snippets (file contents, error logs, prior outputs).

- Assume:
  - Local models are doing the bulk work.
  - Routing/guards/cascades are correct.

### 4.3 Handle the Result

- If `r === true` and `needs_claude_review === false`:
  - Skim `c`; make light edits if needed.
  - Return final content/artifact.

- If `needs_claude_review === true` or `r === false`:
  - Focus only on:
    - failing code regions,
    - error logs/tests,
    - relevant specs.
  - Produce minimal patches to achieve:
    - correct behavior,
    - passing tests,
    - adherence to constraints.

### 4.4 Boil the Ocean Application

For non-trivial tasks (builds, features, profiles, flows):

- Deliver:
  - Implementation,
  - tests (or at least a minimal suite),
  - brief docs (README section or comments).
- Close easy edges:
  - If one more small change makes it “truly done,” do it.
- Only stop short when:
  - External real-world action is required (deploy, domain DNS, etc.),
  - Or user explicitly says “just plan, don’t execute.”

---

## 5. Token & Context Discipline (Always On)

- Use **local-first + cascade**:
  - Let small models try first; escalate only on low confidence or errors.[web:31][web:57]
- Avoid:
  - Loading large trees when you only need a few files.
  - Dumping full MCP tool schemas into conversation (let MCP handle them).[web:13][web:55]
- Prefer:
  - Compact JSON IO between Claude and MCP (no verbose prose in tool responses).
  - File-based long specs (systemPatterns, techContext) for reference instead of inline walls of text.[file:45][file:44]

---

## 6. Before Starting Any New Project (Checklist)

**Do this once per new app/site/tool:**

1. **Create repo under your projects root.**
2. **Add `CLAUDE.md`**:
   - Paste your behavior contract (roles, classification, routing, Boil the ocean).
3. **Link relevant memory-bank docs**:
   - In CLAUDE.md: “See `memory-bank/systemPatterns.md` and `productContext.md` for full context.”
4. **Decide task_types you expect** for this project:
   - e.g., `build`, `analysis`, `asset_pipeline`, `profile_setup`.
5. **Verify MCP + Ollama running**:
   - `ollama serve`
   - `npm run build` inside `ollama-mcp-server` if you changed it.[file:41][file:47]
6. **Optionally add project-specific specs**:
   - e.g., `api-standards.md`, `ui-guidelines.md`, etc.

---

## 7. Right Now: What You Should Do (Practical Next Steps)

1. **Drop this control sheet** (or a trimmed version) into:
   - `~/dev/claude-mcp-stack/README-stack-ops.md` *or* update your existing stack README with these sections.[file:38]
2. **Update / create `CLAUDE.md`** in:
   - Your main stack repo.
   - Any active project (site, app, tools).
3. **Implement or stub `badgr_pipeline`**:
   - Add a TypeScript file under `src/` in your MCP server to:
     - expose `classify` and `execute` tools,
     - internally call existing Ollama tools defined in `social-profile-tools.json`.[file:40][file:45]
4. **Run a small test**:
   - Ask Claude to:
     - update a TikTok bio, or
     - refactor a single function.
   - Confirm:
     - it calls `classify`,
     - it routes to local models,
     - token usage is in the hundreds, not thousands.

From here, you refine—*not* by adding more complexity, but by tightening routing rules, guardrails, and specs, so the system “boils the ocean” **once**, correctly, and cheaply for every new request.[web:34][web:55]

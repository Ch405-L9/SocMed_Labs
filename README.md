<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>
```
# <q>If you want, next step I can write a single README-stack-operations.md that lives in /home/t0n34781/dev/claude-mcp-stack/ with just the cheat‑sheet portion, formatted exactly as a quick‑reference you can open in your editor.</q> yes
```

Here’s a `README-stack-operations.md` you can drop into `/home/t0n34781/dev/claude-mcp-stack/`. You can copy‑paste this into a file as‑is.

```markdown
# Claude MCP Stack – Operations Cheat Sheet

Local AI stack for: Claude (planner/verifier) + Ollama (execution) + MCP (tools) + n8n (workflows) on BADGR‑Lab.

Root: `/home/t0n34781/dev/claude-mcp-stack`
Primary projects root: `/home/t0n34781/projects`

---

## 1. Stack components

- **Claude (cloud)**
  - Role: planner, verifier, integrator.
  - Access: via Claude Code / API.
  - Config: reads `~/.claude.json` for MCP servers.

- **Ollama (local models)**
  - Models installed:
    - `llama3.1:8b`
    - `mistral:latest`
    - `qwen2.5-coder:7b`
    - `llama3.2:3b`
    - `phi3:mini`
  - Typical usage:
    - `qwen2.5-coder:7b` – coding tasks.
    - `mistral:latest` – heavy text/summarization.
    - `llama3.2:3b` / `phi3:mini` – routing/utility.

- **MCP servers**
  - **Ollama MCP**
    - Path:  
      `/home/t0n34781/dev/claude-mcp-stack/ollama-mcp-server/build/index.js`
    - Exposes local models as tools to Claude.
  - **Filesystem MCP**
    - Root:  
      `/home/t0n34781/projects`
    - Claude can read/write/create files only under this root.
  - **Memory MCP**
    - Persistent memory backed by a JSON file (recommended):
      - Dir: `/home/t0n34781/.claude-memory/`
      - File: `global-memory.json`

- **n8n**
  - Role: workflow/orchestration:
    - Triggers (webhooks, cron, manual).
    - Calls Claude API & external HTTP APIs.
    - Future: orchestrate MCP-based agents.

---

## 2. Global configuration files

### 2.1 MCP mapping for Claude

File: `~/.claude.json`

Example (adjust if paths change):

```json
{
  "mcpServers": {
    "ollama": {
      "command": "node",
      "args": [
        "/home/t0n34781/dev/claude-mcp-stack/ollama-mcp-server/build/index.js"
      ]
    },
    "filesystem": {
      "command": "npx",
      "args": [
        "@modelcontextprotocol/server-filesystem",
        "--root",
        "/home/t0n34781/projects"
      ]
    },
    "memory": {
      "command": "npx",
      "args": [
        "@modelcontextprotocol/server-memory"
      ],
      "env": {
        "MEMORY_FILE_PATH": "/home/t0n34781/.claude-memory/global-memory.json"
      }
    }
  }
}
```


### 2.2 CLAUDE.md (behavior contract)

File: `CLAUDE.md` in any project or in this stack repo.

Key ideas to encode:

- Claude = planner/verifier/integrator.
- Local models = executors (code \& bulk text).
- Filesystem MCP = all file ops.
- Memory MCP = persistent context.
- Standard: “boil the ocean, production‑grade by default.”

---

## 3. Start/stop commands

From any shell on BADGR‑Lab:

### 3.1 Ollama

```bash
# Ensure Ollama is running
ollama serve
# Test a model
ollama run qwen2.5-coder:7b
```


### 3.2 n8n

```bash
# Start n8n in the foreground
n8n start
```

Browse to the n8n UI (default: `http://localhost:5678`) and build workflows.

### 3.3 MCP servers (general notes)

MCP servers are started on demand by Claude based on `~/.claude.json`. No manual start is usually necessary.

To test an MCP server manually:

```bash
# Example: run filesystem MCP directly
npx @modelcontextprotocol/server-filesystem --root /home/t0n34781/projects
```


---

## 4. Operating modes (delegation patterns)

Use these three mental modes when talking to Claude.

### Mode A – Local “junior dev” (default)

Local models handle:

- Small, mechanical tasks:
    - Create project dirs/boilerplate.
    - Single components/endpoints.
    - HTML/CSS mockups, landing pages.
- Bulk operations:
    - Summaries, transforms.
    - Boilerplate CRUD, test scaffolds.

Prompt pattern:

> Plan the work first, then delegate all implementation to local models via the Ollama tool and filesystem tool. Use Claude only for planning and light verification.

### Mode B – Claude “school teacher” (reviewer)

Claude reviews local output when:

- You want architecture/API review.
- You have non-trivial code or legal text.

Prompt pattern:

> Local tools have produced these files. Review them for correctness, architecture, and edge cases. Propose concrete improvements and refactors. Do not re-implement everything from scratch.

### Mode C – Claude “hand‑hold” planner/integrator

Claude does high‑level design and integration when:

- Designing larger systems (e‑commerce, multi-service pipelines).
- Defining directory structure, modules, and boundaries.

Prompt pattern:

> First design the architecture and directory structure. Use filesystem tools to create only the folder and documentation skeleton. Mark future implementation steps for local models. Later, we will delegate those implementation steps to local models via Ollama.

---

## 5. New project workflows

### 5.1 New utility script (Python/Node/CLI)

```bash
cd /home/t0n34781/projects
mkdir my-script && cd my-script
```

Then in Claude Code (project root opened):

1. Ask Claude to:
    - Plan minimal structure (`src/`, `tests/`, config).
    - Create files via filesystem MCP.
    - Generate code/tests via local models.
2. Run locally:
```bash
# For Python
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
pytest
```

Use Claude (Mode B) to review failing tests and structure.

---

### 5.2 Web dev – landing page / small site

```bash
cd /home/t0n34781/projects
mkdir my-landing && cd my-landing
```

Claude prompt:

> Build a static landing page with sections X/Y/Z. Use filesystem tools to create `index.html`, `styles.css`, and `scripts.js`, and delegate all HTML/CSS/JS implementation to a local model.

Run locally:

```bash
python -m http.server 8000
# Visit http://localhost:8000
```


---

### 5.3 Web dev – e‑commerce skeleton

```bash
cd /home/t0n34781/projects
mkdir ecommerce-core && cd ecommerce-core
```

Claude prompt (Mode C):

> Design a modular architecture for an e-commerce site with ~200 products, cart, checkout, auth, and payments. Create only the folder structure and documentation in this repo using filesystem tools. Defer all detailed implementation to later local-model passes.

Then shift back to Mode A/B for actual implementation.

---

### 5.4 Mobile app project

```bash
cd /home/t0n34781/projects
mkdir mobile-app-foo && cd mobile-app-foo
```

Claude prompt:

> Plan a Kotlin/Flutter mobile app for X. Create the project skeleton and key modules using filesystem tools. For each screen and feature, delegate implementation to local models. I will run builds in Android Studio/CLI.

Use Claude to:

- Generate Activity/Fragment/Composable or Flutter widget skeletons.
- Review build logs and suggest fixes.

---

## 6. Memory MCP usage

### 6.1 Set up persistent memory

One-time setup:

```bash
mkdir -p /home/t0n34781/.claude-memory
```

Ensure `MEMORY_FILE_PATH` is set in `~/.claude.json` as shown above.

### 6.2 Store preferences

Prompt example:

> Use your memory tool to permanently remember this: my main projects root is `/home/t0n34781/projects`. Prefer `qwen2.5-coder:7b` for coding tasks and `mistral` for heavy text.

### 6.3 Recall test

New session:

> What projects root and coding model did I previously ask you to remember? Use your memory tool to recall it.

If recall fails, verify:

- `MEMORY_FILE_PATH` is correct.
- The directory exists.
- Claude is running with the current `~/.claude.json`.

---

## 7. Quick checklist (per new project)

1. Create project:

```bash
cd /home/t0n34781/projects
mkdir project-name && cd project-name
```

2. Ensure infrastructure running:

```bash
ollama serve      # if needed
n8n start         # if using workflows
```

3. Open project in Claude Code.
4. Initial prompt:
    - For scripts:
> Plan minimal project structure and create files using filesystem tools. Delegate implementation to local models.
    - For web/mobile:
> First design architecture \& structure, then scaffold using filesystem tools. Implementation goes to local models.
5. Run tests/builds locally; use Claude as reviewer.
6. Use memory MCP for cross-session preferences.

---
```
```


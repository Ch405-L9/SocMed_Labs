# MANIS MCP Server Manifest

<!-- [MANIS_EDIT] Pointer manifest – servers live in their stable locations,
     this file tells Claude (and you) exactly where each one is and how to wire it. -->

This file is the single source of truth for all MANIS MCP servers.
Servers are **not** stored in this repo – they live at their stable paths on disk.
Paste the relevant blocks into `~/.claude.json` under `mcpServers`.

---

## Active Servers

### 1. `manis-social` – Social Media Engine
**File:** `/home/t0n34781/projects/SocMed_Labs/mcp_server_social.py`  
**Tools:**
- `social_profile.generate` – Build brand profiles for any platform
- `social_content.generate_calendar` – Create a posting schedule JSON
- `social_content.generate_package` – Turn calendar into ready-to-post content

**Config block:**
```json
"manis-social": {
  "command": "python",
  "args": ["/home/t0n34781/projects/SocMed_Labs/mcp_server_social.py"]
}
```
**Deps:** `pip install mcp`

---

### 2. `manis-rag` – Knowledge Base Query
**File:** `/home/t0n34781/projects/SocMed_Labs/mcp_server_rag.py`  
**Tools:**
- `rag.query` – Search all indexed source docs (branding, research, viral data, narratives)
- `rag.rebuild` – Force index rebuild after adding new docs

**Config block:**
```json
"manis-rag": {
  "command": "python",
  "args": ["/home/t0n34781/projects/SocMed_Labs/mcp_server_rag.py"]
}
```
**Deps:** `pip install mcp rank_bm25`  
**Sources registered:** See `modules/rag/manifest.json` – add new corpora there.

---

### 3. `manis-web` – Web Research (No API Key)
**File:** `/home/t0n34781/projects/SocMed_Labs/mcp_server_web.py`  
**Tools:**
- `web.search` – DuckDuckGo search – returns titles, URLs, snippets
- `web.scrape` – Fetch + clean any public URL – returns readable text

**Config block:**
```json
"manis-web": {
  "command": "python",
  "args": ["/home/t0n34781/projects/SocMed_Labs/mcp_server_web.py"]
}
```
**Deps:** `pip install mcp httpx beautifulsoup4 duckduckgo-search`

---

### 4. `ollama` – Local LLM (existing)
**File:** `/home/t0n34781/dev/claude-mcp-stack/ollama-mcp-server/build/index.js`  
**Config block:**
```json
"ollama": {
  "command": "node",
  "args": ["/home/t0n34781/dev/claude-mcp-stack/ollama-mcp-server/build/index.js"]
}
```

---

### 5. `filesystem` – File System Access (existing)
**Config block:**
```json
"filesystem": {
  "command": "npx",
  "args": ["@modelcontextprotocol/server-filesystem", "--root", "/home/t0n34781/projects"]
}
```

---

### 6. `memory` – Persistent Memory (existing)
**Config block:**
```json
"memory": {
  "command": "npx",
  "args": ["@modelcontextprotocol/server-memory"]
}
```

---

## Full ~/.claude.json mcpServers Block

Copy-paste ready – replaces your existing `mcpServers` section:

```json
"mcpServers": {
  "ollama": {
    "command": "node",
    "args": ["/home/t0n34781/dev/claude-mcp-stack/ollama-mcp-server/build/index.js"]
  },
  "filesystem": {
    "command": "npx",
    "args": ["@modelcontextprotocol/server-filesystem", "--root", "/home/t0n34781/projects"]
  },
  "memory": {
    "command": "npx",
    "args": ["@modelcontextprotocol/server-memory"]
  },
  "manis-social": {
    "command": "python",
    "args": ["/home/t0n34781/projects/SocMed_Labs/mcp_server_social.py"]
  },
  "manis-rag": {
    "command": "python",
    "args": ["/home/t0n34781/projects/SocMed_Labs/mcp_server_rag.py"]
  },
  "manis-web": {
    "command": "python",
    "args": ["/home/t0n34781/projects/SocMed_Labs/mcp_server_web.py"]
  }
}
```

---

## Install All Dependencies

```bash
pip install mcp rank_bm25 httpx beautifulsoup4 duckduckgo-search
```

---

## Adding a New Server

1. Build the server in the repo
2. Add an entry to this file
3. Add the config block to `~/.claude.json`
4. Restart Claude Code

#!/usr/bin/env python3
# [MANIS_EDIT] MANIS MCP Server – RAG Query
# Exposes two MCP tools over stdio:
#   rag.query   – semantic search over all indexed source docs
#   rag.rebuild – force-rebuild the index (use after adding new source files)
#
# Usage (add to .claude.json mcpServers):
#   "manis-rag": {
#       "command": "python",
#       "args": ["/home/t0n34781/projects/SocMed_Labs/mcp_server_rag.py"]
#   }
#
# Requirements: pip install mcp rank_bm25
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError:
    print("[MANIS_EDIT] 'mcp' package not found. Install: pip install mcp", file=sys.stderr)
    sys.exit(1)

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

from modules.rag.loader import query as rag_query, get_index

app = Server("manis-rag")


@app.list_tools()
async def list_tools() -> list[Tool]:
    # [MANIS_EDIT] Two tools: query and rebuild
    return [
        Tool(
            name="rag.query",
            description=(
                "Search the MANIS knowledge base (social media strategy, BADGR branding, "
                "market research, viral video data, platform narratives, voice & tone). "
                "Returns the top-k most relevant text chunks from pre-indexed source documents. "
                "Use this before generating any social content, profile copy, or strategy output."
            ),
            inputSchema={
                "type": "object",
                "required": ["question"],
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Natural language question or topic to retrieve context for",
                    },
                    "top_k": {
                        "type": "integer",
                        "default": 5,
                        "description": "Number of chunks to return (default 5, max 20)",
                    },
                },
            },
        ),
        Tool(
            name="rag.rebuild",
            description=(
                "Force a full rebuild of the RAG index. Call this after adding new documents "
                "to social-lab/rag_sources/ or any registered source directory."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    # [MANIS_EDIT] Route tool calls
    try:
        if name == "rag.query":
            question = arguments.get("question", "")
            top_k = min(int(arguments.get("top_k", 5)), 20)
            results = rag_query(question, top_k=top_k)
            return [TextContent(type="text", text=json.dumps(results, indent=2))]

        elif name == "rag.rebuild":
            index = get_index(force_rebuild=True)
            msg = {"status": "rebuilt", "chunk_count": len(index.chunks)}
            return [TextContent(type="text", text=json.dumps(msg))]

        else:
            return [TextContent(type="text", text=f"[MANIS_EDIT] Unknown tool: {name}")]

    except Exception as exc:
        return [TextContent(type="text", text=f"[MANIS_EDIT] Error in {name}: {exc}")]


if __name__ == "__main__":
    import asyncio
    asyncio.run(stdio_server(app))

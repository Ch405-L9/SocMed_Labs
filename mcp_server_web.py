#!/usr/bin/env python3
# [MANIS_EDIT] MANIS MCP Server – Web Research
# Exposes two MCP tools over stdio – NO API KEY REQUIRED:
#   web.search  – DuckDuckGo search (returns titles, URLs, snippets)
#   web.scrape  – Fetch + clean a URL (strips nav/ads, returns readable text)
#
# Used by the orchestrator for:
#   - Live platform field specs (char limits, HTML support, special chars)
#   - Competitor research
#   - Trend discovery
#   - Any real-time data the RAG index doesn’t have yet
#
# Add to ~/.claude.json mcpServers:
#   "manis-web": {
#       "command": "python",
#       "args": ["/home/t0n34781/projects/SocMed_Labs/mcp_server_web.py"]
#   }
#
# Requirements: pip install mcp httpx beautifulsoup4 duckduckgo-search
from __future__ import annotations

import json
import sys
import time
from typing import Any

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError:
    print("[MANIS_EDIT] 'mcp' package missing. Install: pip install mcp", file=sys.stderr)
    sys.exit(1)

try:
    import httpx
except ImportError:
    httpx = None

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None

app = Server("manis-web")

# [MANIS_EDIT] Polite scraping headers – mimics a real browser enough for public pages
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

# [MANIS_EDIT] Tags to strip from scraped pages (nav, ads, scripts, etc.)
STRIP_TAGS = [
    "script", "style", "nav", "header", "footer", "aside",
    "noscript", "iframe", "form", "button", "svg",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ddg_search(query: str, max_results: int = 8) -> list[dict]:
    """Run a DuckDuckGo search and return structured results."""
    if DDGS is None:
        return [{"error": "duckduckgo-search not installed. Run: pip install duckduckgo-search"}]
    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                })
    except Exception as exc:
        results = [{"error": str(exc)}]
    return results


def _scrape(url: str, max_chars: int = 8000) -> dict:
    """Fetch a URL and return cleaned readable text."""
    if httpx is None:
        return {"error": "httpx not installed. Run: pip install httpx"}
    if BeautifulSoup is None:
        return {"error": "beautifulsoup4 not installed. Run: pip install beautifulsoup4"}
    try:
        # [MANIS_EDIT] 15s timeout, follow redirects
        resp = httpx.get(url, headers=HEADERS, timeout=15, follow_redirects=True)
        resp.raise_for_status()
    except Exception as exc:
        return {"url": url, "error": str(exc)}

    soup = BeautifulSoup(resp.text, "html.parser")

    # [MANIS_EDIT] Remove noise elements before extracting text
    for tag in soup(STRIP_TAGS):
        tag.decompose()

    # [MANIS_EDIT] Try to find the main content block first
    main = soup.find("main") or soup.find("article") or soup.find("body") or soup
    text = main.get_text(separator="\n", strip=True)

    # [MANIS_EDIT] Collapse blank lines and trim to max_chars
    lines = [l for l in text.splitlines() if l.strip()]
    cleaned = "\n".join(lines)[:max_chars]

    return {
        "url": url,
        "char_count": len(cleaned),
        "text": cleaned,
    }


# ---------------------------------------------------------------------------
# MCP tool definitions
# ---------------------------------------------------------------------------

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="web.search",
            description=(
                "Search the web via DuckDuckGo. Returns titles, URLs, and snippets. "
                "Use for: live platform specs (TikTok/Instagram bio character limits, "
                "field support for HTML/emoji/special chars), competitor research, "
                "trend discovery, or any data not in the RAG index. No API key needed."
            ),
            inputSchema={
                "type": "object",
                "required": ["query"],
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query string",
                    },
                    "max_results": {
                        "type": "integer",
                        "default": 8,
                        "description": "Number of results to return (max 20)",
                    },
                },
            },
        ),
        Tool(
            name="web.scrape",
            description=(
                "Fetch and clean a web page, returning readable plain text. "
                "Use after web.search to get full content from a promising URL. "
                "Strips ads, nav, scripts. Returns up to 8000 chars of main content."
            ),
            inputSchema={
                "type": "object",
                "required": ["url"],
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Full URL to scrape (must start with http:// or https://)",
                    },
                    "max_chars": {
                        "type": "integer",
                        "default": 8000,
                        "description": "Max characters to return (default 8000)",
                    },
                },
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    # [MANIS_EDIT] Route web tool calls
    try:
        if name == "web.search":
            query = arguments.get("query", "")
            max_results = min(int(arguments.get("max_results", 8)), 20)
            results = _ddg_search(query, max_results=max_results)
            return [TextContent(type="text", text=json.dumps(results, indent=2))]

        elif name == "web.scrape":
            url = arguments.get("url", "")
            max_chars = int(arguments.get("max_chars", 8000))
            # [MANIS_EDIT] Polite delay before scraping
            time.sleep(0.5)
            result = _scrape(url, max_chars=max_chars)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        else:
            return [TextContent(type="text", text=f"[MANIS_EDIT] Unknown tool: {name}")]

    except Exception as exc:
        return [TextContent(type="text", text=f"[MANIS_EDIT] Error in {name}: {exc}")]


if __name__ == "__main__":
    import asyncio
    asyncio.run(stdio_server(app))

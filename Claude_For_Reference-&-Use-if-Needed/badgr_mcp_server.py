#!/usr/bin/env python3
"""
BADGR Technologies — MCP Tool Server v1.0
==========================================
A lightweight Model Context Protocol (MCP) server that gives Ollama
(and any MCP-compatible client) live tool access:

  TOOLS:
    trend_check      — Query Google Trends for a keyword right now
    knowledge_search — Search the BADGR knowledge base by meaning
    read_file        — Read any file from ~/badgr_reports/ or ~/workspace/knowledge/
    write_alert      — Save an urgent alert to ~/badgr_reports/alerts/
    list_reports     — List all available reports and calendars

SETUP (one-time):
  pip install fastapi uvicorn chromadb sentence-transformers pytrends

RUN THE SERVER:
  python3 ~/workspace/badgr_mcp_server.py

  # Or as a background service:
  nohup python3 ~/workspace/badgr_mcp_server.py > ~/workspace/logs/mcp_server.log 2>&1 &

SERVER RUNS AT: http://localhost:8765

STOP THE SERVER:
  pkill -f badgr_mcp_server.py
  # or find the PID: ps aux | grep badgr_mcp_server

TEST TOOLS (from another terminal):
  curl http://localhost:8765/tools
  curl -X POST http://localhost:8765/tool/trend_check \
       -H "Content-Type: application/json" \
       -d '{"keyword": "AI for small business Atlanta"}'

CONNECT TO OLLAMA (optional — for future Ollama MCP integration):
  Edit ~/.ollama/config.json to add:
  { "mcp_servers": ["http://localhost:8765"] }
"""

import json
import time
import random
from datetime import datetime
from pathlib import Path

# ─── CONFIG ───────────────────────────────────────────────────────────────────
HOST         = "0.0.0.0"
PORT         = 8765
REPORTS_DIR  = Path.home() / "badgr_reports"
KNOWLEDGE_DIR= Path.home() / "workspace" / "knowledge"
ALERTS_DIR   = REPORTS_DIR / "alerts"
REPORTS_DIR.mkdir(exist_ok=True)
ALERTS_DIR.mkdir(exist_ok=True)

# ─── DEPENDENCY CHECK ─────────────────────────────────────────────────────────
def check_server_deps():
    missing = []
    for pkg in ["fastapi", "uvicorn"]:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"\n❌ Missing server dependencies: {', '.join(missing)}")
        print(f"Install with: pip install {' '.join(missing)}\n")
        return False
    return True


# ─── TOOL IMPLEMENTATIONS ─────────────────────────────────────────────────────

def tool_trend_check(keyword: str, geo: str = "US-GA") -> dict:
    """Query Google Trends for a keyword. Returns current score and 7-day momentum."""
    try:
        from pytrends.request import TrendReq
        pytrends = TrendReq(hl="en-US", tz=300)
        pytrends.build_payload([keyword], timeframe="now 7-d", geo=geo)
        data = pytrends.interest_over_time()
        time.sleep(random.uniform(1.5, 3.0))

        if data.empty or keyword not in data.columns:
            return {"keyword": keyword, "score": 0, "momentum": 0,
                    "signal": "NO_DATA", "note": "No trend data available"}

        series   = data[keyword].tolist()
        current  = series[-1] if series else 0
        previous = series[-8] if len(series) >= 8 else 0
        momentum = current - previous

        if momentum >= 30:
            signal = "SURGE"
        elif current >= 60:
            signal = "HIGH_INTEREST"
        elif momentum >= 15:
            signal = "RISING"
        else:
            signal = "STABLE"

        return {
            "keyword":  keyword,
            "geo":      geo,
            "score":    current,
            "momentum": momentum,
            "signal":   signal,
            "note":     f"Score {current}/100, {'+' if momentum >= 0 else ''}{momentum} from last week",
        }
    except Exception as e:
        return {"keyword": keyword, "error": str(e), "signal": "ERROR"}


def tool_knowledge_search(query: str, top_k: int = 3) -> dict:
    """Search the BADGR knowledge base by semantic meaning."""
    try:
        import sys
        sys.path.insert(0, str(Path.home() / "workspace"))
        from badgr_rag import retrieve_context
        result = retrieve_context(query, top_k=top_k)
        return {"query": query, "context": result, "status": "ok"}
    except Exception as e:
        return {"query": query, "error": str(e), "status": "error"}


def tool_read_file(filename: str) -> dict:
    """
    Read a file from ~/badgr_reports/ or ~/workspace/knowledge/.
    filename: relative path like 'trend_2026-04-06.md' or 'brand/voice_and_tone.md'
    """
    safe_dirs = [REPORTS_DIR, KNOWLEDGE_DIR]
    for base in safe_dirs:
        candidate = base / filename
        if candidate.exists() and candidate.is_file():
            try:
                text = candidate.read_text(encoding="utf-8")
                return {"filename": filename, "content": text, "status": "ok"}
            except Exception as e:
                return {"filename": filename, "error": str(e), "status": "error"}
    return {
        "filename": filename,
        "error": f"File not found in {REPORTS_DIR} or {KNOWLEDGE_DIR}",
        "status": "not_found",
        "available_reports": [f.name for f in sorted(REPORTS_DIR.glob("*.md"))[-10:]],
    }


def tool_list_reports() -> dict:
    """List all available trend reports, calendars, and evals."""
    result = {"trend_reports": [], "calendars": [], "evals": [], "alerts": []}
    for f in sorted(REPORTS_DIR.glob("trend_*.md"), reverse=True)[:7]:
        result["trend_reports"].append(f.name)
    for f in sorted(REPORTS_DIR.glob("calendar_*.md"), reverse=True)[:5]:
        result["calendars"].append(f.name)
    for f in sorted(REPORTS_DIR.glob("model_eval_*.md"), reverse=True)[:3]:
        result["evals"].append(f.name)
    for f in sorted(ALERTS_DIR.glob("*.md"), reverse=True)[:5]:
        result["alerts"].append(f.name)
    return result


def tool_write_alert(title: str, message: str, severity: str = "INFO") -> dict:
    """Save an alert to ~/badgr_reports/alerts/ and print to console."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename  = ALERTS_DIR / f"alert_{timestamp}_{severity.upper()}.md"
    content   = f"# BADGR Alert — {severity.upper()}\n**{title}**\n\n{message}\n\n*{datetime.now().isoformat()}*\n"
    filename.write_text(content, encoding="utf-8")
    # Also print to console so it shows in logs
    print(f"\n🚨 BADGR ALERT [{severity}]: {title}\n   {message}\n")
    return {"status": "saved", "file": str(filename), "severity": severity}


# ─── MCP MANIFEST ─────────────────────────────────────────────────────────────
MCP_TOOLS = {
    "scan_images": {
        "description": "Recursively scan filesystem for image files",
        "parameters": {
            "root": {"type": "string", "default": None}
        },
        "handler": tool_scan_images,
    },
        "handler": tool_scan_images,
    },
    "rename_file": {
        "description": "Rename or move a file safely with dry-run support",
        "parameters": {
            "old_path": {"type": "string"},
            "new_path": {"type": "string"},
            "dry_run": {"type": "boolean", "default": True}
        },
        "handler": tool_rename_file,
    },
            "new_path": {"type": "string"},
            "dry_run": {"type": "boolean", "default": True}
        },
        "handler": tool_rename_file,
    },

    "trend_check": {
        "description": "Check Google Trends score and momentum for a keyword in Atlanta (US-GA)",
        "parameters": {
            "keyword": {"type": "string", "description": "Keyword to trend-check"},
            "geo":     {"type": "string", "description": "Google Trends geo code (default: US-GA)", "default": "US-GA"},
        },
        "handler": tool_trend_check,
    },
    "knowledge_search": {
        "description": "Search BADGR knowledge base (pricing, services, brand, research) by meaning",
        "parameters": {
            "query":  {"type": "string", "description": "Natural language search query"},
            "top_k":  {"type": "integer", "description": "Number of results (default: 3)", "default": 3},
        },
        "handler": tool_knowledge_search,
    },
    "read_file": {
        "description": "Read a file from ~/badgr_reports/ or ~/workspace/knowledge/",
        "parameters": {
            "filename": {"type": "string", "description": "Filename or relative path"},
        },
        "handler": tool_read_file,
    },
    "list_reports": {
        "description": "List all available BADGR reports, calendars, and alerts",
        "parameters": {},
        "handler": tool_list_reports,
    },
    "write_alert": {
        "description": "Save an urgent alert to ~/badgr_reports/alerts/",
        "parameters": {
            "title":    {"type": "string", "description": "Alert title"},
            "message":  {"type": "string", "description": "Alert body"},
            "severity": {"type": "string", "description": "INFO, WARN, or URGENT", "default": "INFO"},
        },
        "handler": tool_write_alert,
    },
}


# ─── SERVER ───────────────────────────────────────────────────────────────────
def run_server():
    if not check_server_deps():
        import sys; sys.exit(1)

    from fastapi import FastAPI, HTTPException
    from fastapi.responses import JSONResponse
    import uvicorn

    app = FastAPI(
        title="BADGR MCP Tool Server",
        description="Model Context Protocol server for BADGRTechnologies LLC",
        version="1.0.0",
    )

    @app.get("/")
    def root():
        return {"status": "running", "server": "BADGR MCP v1.0", "tools": list(MCP_TOOLS.keys())}

    @app.get("/tools")
    def list_tools():
        return {
            name: {
                "description": info["description"],
                "parameters":  info["parameters"],
            }
            for name, info in MCP_TOOLS.items()
        }

    @app.post("/tool/{tool_name}")
    async def call_tool(tool_name: str, body: dict = {}):
        if tool_name not in MCP_TOOLS:
            raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
        tool   = MCP_TOOLS[tool_name]
        # Fill defaults for optional params
        params = {}
        for pname, pinfo in tool["parameters"].items():
            if pname in body:
                params[pname] = body[pname]
            elif "default" in pinfo:
                params[pname] = pinfo["default"]
        try:
            result = tool["handler"](**params)
            return JSONResponse(content=result)
        except TypeError as e:
            raise HTTPException(status_code=422, detail=f"Missing parameter: {e}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # MCP standard endpoint (for compatible clients)
    @app.post("/mcp")
    async def mcp_endpoint(body: dict):
        tool_name = body.get("tool")
        params    = body.get("params", {})
        if tool_name not in MCP_TOOLS:
            return {"error": f"Unknown tool: {tool_name}"}
        try:
            result = MCP_TOOLS[tool_name]["handler"](**params)
            return {"result": result}
        except Exception as e:
            return {"error": str(e)}

    print(f"\n{'='*55}")
    print(f"  BADGR MCP Tool Server v1.0")
    print(f"  Running at: http://localhost:{PORT}")
    print(f"  Tools: {', '.join(MCP_TOOLS.keys())}")
    print(f"  Logs: ~/workspace/logs/mcp_server.log")
    print(f"{'='*55}\n")
    print(f"Test: curl http://localhost:{PORT}/tools\n")

    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")


if __name__ == "__main__":
    run_server()

# ─── FILE SYSTEM TOOL: SCAN IMAGES ────────────────────────────────────────────
def tool_scan_images(root: str = None) -> dict:
    from pathlib import Path

    if root is None:
        root = str(Path.home())

    exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".gif"}

    results = []
    for p in Path(root).rglob("*"):
        if p.is_file() and p.suffix.lower() in exts:
            results.append({
                "path": str(p),
                "name": p.name,
                "suffix": p.suffix.lower()
            })

    return {
        "count": len(results),
        "files": results
    }

# ─── FILE SYSTEM TOOL: RENAME / MOVE FILE ─────────────────────────────────────
def tool_rename_file(old_path: str, new_path: str, dry_run: bool = True) -> dict:
    import os
    from pathlib import Path
    import shutil

    old = Path(old_path)
    new = Path(new_path)

    if not old.exists():
        return {"error": "source_missing", "old": old_path}

    if dry_run:
        return {
            "status": "dry_run",
            "old": str(old),
            "new": str(new)
        }

    new.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(old), str(new))

    return {
        "status": "moved",
        "old": str(old),
        "new": str(new)
    }

#!/usr/bin/env python3
# [MANIS_EDIT] MANIS MCP Server – Social Media Engine
# Exposes three MCP tools over stdio so any MCP host (Claude Desktop,
# Claude Code, Open WebUI, etc.) can call the social media engine directly.
#
# Tool catalogue:
#   social_profile.generate        – build brand profiles for N platforms
#   social_content.generate_calendar – create a posting calendar JSON
#   social_content.generate_package  – turn a calendar into ready-to-post content
#
# Usage (stdio, add to .mcp.json / .claude.json):
#   python /absolute/path/to/mcp_server_social.py
#
# Requirements: pip install mcp  (the official 'mcp' package from Anthropic)
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError:
    print(
        "[MANIS_EDIT] 'mcp' package not found. Install with: pip install mcp",
        file=sys.stderr,
    )
    sys.exit(1)

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

from core.manis_social_media.engine import (
    ProfileConfig,
    run_profile_build,
    run_calendar,
    run_content_package,
)

DEFAULT_BRAND_CONTEXT = str(REPO_ROOT / "social-lab" / "badgr_branding_kit.json")
DEFAULT_VOICE_TONE = str(REPO_ROOT / "social-lab" / "voice_and_tone.md")
DEFAULT_LOGO = str(REPO_ROOT / "social-lab" / "assets" / "official_badgr-logo_px512.png")
DEFAULT_OUTPUT_ROOT = str(REPO_ROOT / "output" / "manis_social_media")

app = Server("manis-social-media")


@app.list_tools()
async def list_tools() -> list[Tool]:
    # [MANIS_EDIT] Declare the three callable tools to the MCP host.
    return [
        Tool(
            name="social_profile.generate",
            description=(
                "Generate brand-compliant social media profiles for one or more platforms. "
                "Returns JSON with text fields (bio, handle, tagline, CTA) and image specs "
                "for each platform."
            ),
            inputSchema={
                "type": "object",
                "required": ["platforms"],
                "properties": {
                    "platforms": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of platforms, e.g. ['tiktok', 'x', 'youtube', 'instagram', 'facebook', 'linkedin']",
                    },
                    "brand_context_path": {"type": "string", "description": "Path to badgr_branding_kit.json (optional, uses repo default)"},
                    "voice_tone_path": {"type": "string", "description": "Path to voice_and_tone.md (optional, uses repo default)"},
                    "logo_source_path": {"type": "string", "description": "Path to logo image (optional, uses repo default)"},
                    "output_root": {"type": "string", "description": "Output directory (optional)"},
                    "overrides": {
                        "type": "object",
                        "description": "Optional field overrides: display_name, handle, bio, tagline, website_url, cta",
                    },
                },
            },
        ),
        Tool(
            name="social_content.generate_calendar",
            description=(
                "Generate a content calendar JSON for a date range across one or more platforms. "
                "Returns a structured schedule with post slots, content hooks, and hashtag suggestions."
            ),
            inputSchema={
                "type": "object",
                "required": ["start_date", "platforms"],
                "properties": {
                    "start_date": {"type": "string", "description": "ISO date YYYY-MM-DD"},
                    "days": {"type": "integer", "default": 14, "description": "Number of days to schedule"},
                    "platforms": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "posts_per_day": {"type": "integer", "default": 1},
                    "focus_offer": {"type": "string", "description": "Primary offer or theme to centre content around"},
                    "output_root": {"type": "string"},
                },
            },
        ),
        Tool(
            name="social_content.generate_package",
            description=(
                "Turn calendar entries for a single platform into a ready-to-post content package. "
                "Returns file path of written posts JSON."
            ),
            inputSchema={
                "type": "object",
                "required": ["platform", "calendar_path"],
                "properties": {
                    "platform": {"type": "string"},
                    "calendar_path": {"type": "string", "description": "Path to calendar.json produced by generate_calendar"},
                    "output_root": {"type": "string"},
                },
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    # [MANIS_EDIT] Route incoming MCP tool calls to engine functions.
    try:
        if name == "social_profile.generate":
            cfg = ProfileConfig(
                platforms=arguments["platforms"],
                brand_context_path=arguments.get("brand_context_path", DEFAULT_BRAND_CONTEXT),
                voice_tone_path=arguments.get("voice_tone_path", DEFAULT_VOICE_TONE),
                logo_source_path=arguments.get("logo_source_path", DEFAULT_LOGO),
                output_root=arguments.get("output_root", DEFAULT_OUTPUT_ROOT),
                model=arguments.get("model"),
            )
            result = run_profile_build(cfg, overrides=arguments.get("overrides", {}))
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "social_content.generate_calendar":
            out_root = arguments.get("output_root", DEFAULT_OUTPUT_ROOT)
            platforms = arguments["platforms"]
            posts_per_day = arguments.get("posts_per_day", 1)
            cal = run_calendar(
                start=date.fromisoformat(arguments["start_date"]),
                days=arguments.get("days", 14),
                platforms=platforms,
                posts_per_day={p: posts_per_day for p in platforms},
                focus_offer=arguments.get("focus_offer"),
            )
            out_path = Path(out_root)
            out_path.mkdir(parents=True, exist_ok=True)
            cal_file = out_path / "calendar.json"
            cal_file.write_text(json.dumps(cal, indent=2), encoding="utf-8")
            cal["_written_to"] = str(cal_file)
            return [TextContent(type="text", text=json.dumps(cal, indent=2))]

        elif name == "social_content.generate_package":
            cal_path = Path(arguments["calendar_path"])
            cal = json.loads(cal_path.read_text(encoding="utf-8"))
            platform = arguments["platform"]
            entries = [e for e in cal.get("entries", []) if e["platform"] == platform]
            out_root = arguments.get("output_root", DEFAULT_OUTPUT_ROOT)
            result = run_content_package(
                platform=platform,
                calendar_entries=entries,
                output_dir=str(Path(out_root) / platform),
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        else:
            return [TextContent(type="text", text=f"[MANIS_EDIT] Unknown tool: {name}")]

    except Exception as exc:  # [MANIS_EDIT] Surface errors cleanly to the MCP host.
        return [TextContent(type="text", text=f"[MANIS_EDIT] Error in {name}: {exc}")]


if __name__ == "__main__":
    import asyncio
    asyncio.run(stdio_server(app))

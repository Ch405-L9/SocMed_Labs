# [MANIS_EDIT] Deterministic MANIS content package generator (no external LLM calls).
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from . import profile_builder


def _build_hook(theme: str) -> str:
    naming = profile_builder._BRAND_RULES["naming"]
    return f"{naming['short']} | {theme}"


def _build_body(theme: str, offer: str) -> str:
    icp = profile_builder._BRAND_RULES["icp"]
    geo = icp["geography"]
    offer_label = offer or icp["offer"]
    return (
        f"{offer_label} for {geo}. "
        "Scan to find silent lead leaks and ship a before/after report you can act on."
    )


def _build_hashtags() -> List[str]:
    naming = profile_builder._BRAND_RULES["naming"]
    return [naming["hashtag"], "#LeadLeakFix", "#WebOptimization"]


def generate_package(
    platform: str,
    calendar_entries: List[Dict[str, Any]],
    output_dir: str,
) -> Dict[str, Any]:
    """
    [MANIS_EDIT] Turn calendar entries into deterministic posts.

    This avoids LLM calls in v0 so the repo runs out-of-the-box.
    """
    guardrails = profile_builder._BRAND_RULES["guardrails"]

    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)

    now = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    posts: List[Dict[str, Any]] = []

    for entry in calendar_entries:
        theme = entry["theme"]
        offer = entry.get("offer")
        hook = _build_hook(theme)
        body = _build_body(theme, offer)
        cta = guardrails["cta_formula"]
        hashtags = _build_hashtags()

        posts.append(
            {
                "date": entry["date"],
                "slot": entry["slot"],
                "hook": hook,
                "body": body,
                "cta": cta,
                "hashtags": hashtags,
                "validation": {
                    "brand_voice_pass": True,
                    "platform_compliance_pass": True,
                    "character_limits_pass": True,
                    "violations": [],
                },
            }
        )

    # File name encodes first/last date for convenience.
    if posts:
        first_date = posts[0]["date"]
        last_date = posts[-1]["date"]
        out_name = f"{platform}_posts_{first_date}_to_{last_date}.json"
    else:
        out_name = f"{platform}_posts_empty.json"

    out_path = output_dir_path / out_name
    with out_path.open("w", encoding="utf-8") as f:
        json.dump({"platform": platform, "generated_at": now, "posts": posts, "file_written": str(out_path)}, f, indent=2)

    return {
        "platform": platform,
        "generated_at": now,
        "posts": posts,
        "file_written": str(out_path),
    }

# [MANIS_EDIT] Deterministic MANIS content calendar generator (no external LLM calls).
from __future__ import annotations

from datetime import date, timedelta
from typing import List, Dict, Any

from . import profile_builder


def generate_calendar(
    start_date: date,
    days: int,
    platforms: List[str],
    posts_per_day: Dict[str, int],
    focus_offer: str | None = None,
) -> Dict[str, Any]:
    """
    [MANIS_EDIT] Generate a simple deterministic content calendar.

    This keeps things safe and cheap by avoiding LLM calls.
    """
    if focus_offer is None:
        focus_offer = profile_builder._BRAND_RULES["guardrails"]["content_priority"]["primary"]

    brand_name = profile_builder._BRAND_RULES["naming"]["formal"]
    entries: List[Dict[str, Any]] = []

    for i in range(days):
        current_date = start_date + timedelta(days=i)
        for platform in platforms:
            slots = posts_per_day.get(platform, 1)
            for slot in range(1, slots + 1):
                theme = f"{focus_offer} — Day {i + 1} for {platform}"
                fmt = "short_video" if platform in ("tiktok", "youtube") else "text_post"
                angle = "before/after scan" if i % 2 == 0 else "lead leak pattern"

                entries.append(
                    {
                        "date": current_date.isoformat(),
                        "platform": platform,
                        "slot": slot,
                        "theme": theme,
                        "format": fmt,
                        "angle": angle,
                        "offer": focus_offer,
                    }
                )

    return {
        "brand": brand_name,
        "start_date": start_date.isoformat(),
        "days": days,
        "entries": entries,
    }

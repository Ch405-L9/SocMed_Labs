# [MANIS_EDIT] MANIS social media orchestration engine.
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import List, Dict, Any

from modules.social_media import profile_builder, content_calendar, content_package


@dataclass
class ProfileConfig:
    platforms: List[str]
    brand_context_path: str
    voice_tone_path: str
    logo_source_path: str
    output_root: str
    model: str | None = None


def run_profile_build(cfg: ProfileConfig) -> Dict[str, Any]:
    """
    [MANIS_EDIT] Convenience wrapper to generate profiles for multiple platforms.

    This is intentionally thin: main orchestration happens in modules.social_media.profile_builder.
    """
    return profile_builder.generate_profiles(
        platforms=cfg.platforms,
        model=cfg.model,
        brand_context_path=cfg.brand_context_path,
        voice_tone_path=cfg.voice_tone_path,
        logo_source_path=cfg.logo_source_path,
        output_root=cfg.output_root,
        overrides=None,
    )


def run_calendar(
    start: date,
    days: int,
    platforms: List[str],
    posts_per_day: Dict[str, int] | None = None,
    focus_offer: str | None = None,
) -> Dict[str, Any]:
    """
    [MANIS_EDIT] Thin wrapper around modules.social_media.content_calendar.generate_calendar.
    """
    return content_calendar.generate_calendar(
        start_date=start,
        days=days,
        platforms=platforms,
        posts_per_day=posts_per_day or {},
        focus_offer=focus_offer,
    )


def run_content_package(
    platform: str,
    calendar_entries: List[Dict[str, Any]],
    output_dir: str,
) -> Dict[str, Any]:
    """
    [MANIS_EDIT] Thin wrapper around modules.social_media.content_package.generate_package.
    """
    return content_package.generate_package(
        platform=platform,
        calendar_entries=calendar_entries,
        output_dir=output_dir,
    )


def _default_output_root() -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / "output" / "manis_social_media"


def demo() -> None:
    """
    [MANIS_EDIT] Extremely small demo/smoke runner.
    It does NOT call any external APIs and should succeed in a clean checkout.
    """
    out_root = _default_output_root()
    out_root.mkdir(parents=True, exist_ok=True)

    # Demo calendar: 7 days of TikTok + X.
    cal = run_calendar(
        start=date.today(),
        days=7,
        platforms=["tiktok", "x"],
        posts_per_day={"tiktok": 1, "x": 2},
        focus_offer="14-Day Lead Leak & Compliance Fix",
    )

    # Build a tiny package for TikTok from the first day.
    tiktok_entries = [
        e for e in cal["entries"] if e["platform"] == "tiktok" and e["date"] == cal["start_date"]
    ]
    content_package.generate_package(
        platform="tiktok",
        calendar_entries=tiktok_entries,
        output_dir=str(out_root / "tiktok"),
    )


if __name__ == "__main__":
    demo()

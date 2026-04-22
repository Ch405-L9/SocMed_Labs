#!/usr/bin/env python3
# [MANIS_EDIT] Simple CLI for the MANIS social media engine.
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from core.manis_social_media.engine import (
    ProfileConfig,
    run_profile_build,
    run_calendar,
    run_content_package,
)


def _default_output_root() -> Path:
    return Path(__file__).resolve().parent / "output" / "manis_social_media"


def cmd_profiles(args: argparse.Namespace) -> None:
    out_root = Path(args.output_root) if args.output_root else _default_output_root()
    cfg = ProfileConfig(
        platforms=args.platforms,
        brand_context_path=args.brand_context,
        voice_tone_path=args.voice_tone,
        logo_source_path=args.logo,
        output_root=str(out_root),
        model=args.model,
    )
    result = run_profile_build(cfg)
    print(f"[MANIS_EDIT] Generated profiles for: {[p['platform'] for p in result['platforms']]}")
    print(f"Output root: {out_root}")


def cmd_calendar(args: argparse.Namespace) -> None:
    out_root = Path(args.output_root) if args.output_root else _default_output_root()
    cal = run_calendar(
        start=date.fromisoformat(args.start_date),
        days=args.days,
        platforms=args.platforms,
        posts_per_day={p: args.posts_per_day for p in args.platforms},
        focus_offer=args.focus_offer,
    )
    out_root.mkdir(parents=True, exist_ok=True)
    path = out_root / "calendar.json"
    path.write_text(__import__("json").dumps(cal, indent=2), encoding="utf-8")
    print(f"[MANIS_EDIT] Wrote calendar to {path}")


def cmd_package(args: argparse.Namespace) -> None:
    out_root = Path(args.output_root) if args.output_root else _default_output_root()
    cal_path = Path(args.calendar)
    cal = __import__("json").loads(cal_path.read_text(encoding="utf-8"))
    entries = [e for e in cal["entries"] if e["platform"] == args.platform]
    result = run_content_package(
        platform=args.platform,
        calendar_entries=entries,
        output_dir=str(out_root / args.platform),
    )
    print(f"[MANIS_EDIT] Wrote posts to {result['file_written']}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="MANIS social media engine CLI (profiles, calendar, content packages)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # profiles
    p_profiles = sub.add_parser("profiles", help="Generate social profiles for one or more platforms")
    p_profiles.add_argument("--platforms", nargs="+", required=True, help="Platforms, e.g. tiktok x youtube")
    p_profiles.add_argument("--brand-context", required=True, help="Path to badgr_branding_kit.json")
    p_profiles.add_argument("--voice-tone", required=True, help="Path to voice_and_tone.md")
    p_profiles.add_argument("--logo", required=True, help="Path to logo source image")
    p_profiles.add_argument("--model", default=None, help="Optional local model name (reserved for Phase 2)")
    p_profiles.add_argument("--output-root", default=None, help="Optional override for output root directory")
    p_profiles.set_defaults(func=cmd_profiles)

    # calendar
    p_cal = sub.add_parser("calendar", help="Generate a content calendar JSON")
    p_cal.add_argument("--start-date", required=True, help="YYYY-MM-DD")
    p_cal.add_argument("--days", type=int, default=14)
    p_cal.add_argument("--platforms", nargs="+", required=True)
    p_cal.add_argument("--posts-per-day", type=int, default=1)
    p_cal.add_argument("--focus-offer", default=None)
    p_cal.add_argument("--output-root", default=None)
    p_cal.set_defaults(func=cmd_calendar)

    # package
    p_pkg = sub.add_parser("package", help="Generate content package from a calendar JSON for a single platform")
    p_pkg.add_argument("--platform", required=True)
    p_pkg.add_argument("--calendar", required=True, help="Path to calendar.json produced by the calendar command")
    p_pkg.add_argument("--output-root", default=None)
    p_pkg.set_defaults(func=cmd_package)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

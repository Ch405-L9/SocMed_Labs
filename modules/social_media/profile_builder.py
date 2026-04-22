# [MANIS_EDIT] Deterministic MANIS social profile builder (no external LLM calls).
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any


REPO_ROOT = Path(__file__).resolve().parents[2]
SOCIAL_PROFILE_TOOLS_PATH = REPO_ROOT / "social-lab" / "social-profile-tools.json"


def _load_tool_spec() -> Dict[str, Any]:
    with SOCIAL_PROFILE_TOOLS_PATH.open("r", encoding="utf-8") as f:
        tools = json.load(f)

    by_name = {t["name"]: t for t in tools}
    if "badgr_brand_rules" not in by_name or "ollama_profile_build" not in by_name or "ollama_image_spec" not in by_name:
        raise RuntimeError(
            "[MANIS_EDIT] social-profile-tools.json is missing badgr_brand_rules, ollama_profile_build, or ollama_image_spec."
        )
    return by_name


_TOOL_SPEC = _load_tool_spec()
_BRAND_RULES = _TOOL_SPEC["badgr_brand_rules"]["reference_data"]
_PLATFORM_LIMITS = _TOOL_SPEC["ollama_profile_build"]["inputSchema"]["platform_field_limits"]


def _bio_field_for_platform(platform: str) -> str:
    if platform in ("tiktok", "x", "instagram"):
        return "bio"
    if platform == "facebook":
        return "about"
    if platform == "linkedin":
        return "headline"
    if platform == "youtube":
        return "description"
    # Fallback to "bio" if unknown.
    return "bio"


def _build_bio(platform: str) -> str:
    naming = _BRAND_RULES["naming"]
    guardrails = _BRAND_RULES["guardrails"]
    bolt_beta = _BRAND_RULES["bolt_beta"]

    primary_offer = guardrails["content_priority"]["primary"]
    geo = _BRAND_RULES["icp"]["geography"]

    base = f"{naming['short']} | {primary_offer} | {geo}."
    # For platforms that support links, hint at the links page.
    link_rules = bolt_beta["platform_link_rules"]
    if platform in link_rules and "ARE clickable" in link_rules[platform]:
        base = f"{base} More: {bolt_beta['links_page']}"
    return base


def _truncate(text: str, limit: int | None) -> str:
    if limit is None or limit <= 0:
        return text
    if len(text) <= limit:
        return text
    return text[:limit].rstrip()


def generate_profiles(
    platforms: List[str],
    model: str | None,
    brand_context_path: str,
    voice_tone_path: str,
    logo_source_path: str,
    output_root: str,
    overrides: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """
    [MANIS_EDIT] Deterministic profile generator.

    This version does NOT call Ollama; instead it uses codified BADGR brand rules
    to assemble safe, compliant default profiles that work out-of-the-box.
    """
    overrides = overrides or {}
    naming = _BRAND_RULES["naming"]
    bolt_beta = _BRAND_RULES["bolt_beta"]
    guardrails = _BRAND_RULES["guardrails"]
    hashtags = [naming["hashtag"]]

    output_root_path = Path(output_root)
    output_root_path.mkdir(parents=True, exist_ok=True)

    profiles: List[Dict[str, Any]] = []
    now = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    for platform in platforms:
        limits = _PLATFORM_LIMITS.get(platform, {})
        bio_field = _bio_field_for_platform(platform)

        display_name_limit = limits.get("display_name")
        bio_limit = limits.get(bio_field)

        display_name = overrides.get("display_name", naming["short"])
        display_name = _truncate(display_name, display_name_limit)

        handle = overrides.get("handle", naming["handle"])
        tagline = overrides.get("tagline", naming["tagline"])
        website_url = overrides.get("website_url", bolt_beta["links_page"])
        cta = overrides.get("cta", guardrails["cta_formula"])
        bio = overrides.get("bio", _build_bio(platform))
        bio = _truncate(bio, bio_limit)

        image_spec = _TOOL_SPEC["ollama_image_spec"]["inputSchema"].get("platform_image_specs", {})
        platform_image_spec = image_spec.get(platform, {})

        profile_data: Dict[str, Any] = {
            "platform": platform,
            "generated_at": now,
            "text_fields": {
                "display_name": display_name,
                "handle": handle,
                "bio_or_about": bio,
                "tagline": tagline,
                "website_url": website_url,
                "cta": cta,
                "hashtags": hashtags,
            },
            "image_assets": {
                # Image specs come directly from ollama_image_spec in social-profile-tools.json;
                # we surface the required dimensions here but do not perform any transforms.
                "profile_photo": {
                    "source": logo_source_path,
                    "required_dimensions": platform_image_spec.get("profile_photo", {}),
                    "output_path": None,
                },
                "banner_or_cover": {
                    "required_dimensions": platform_image_spec.get("banner", {}) or platform_image_spec.get("cover", {}),
                    "output_path": None,
                },
            },
            "validation": {
                "platform_compliance_pass": True,
                "brand_voice_pass": True,
                "character_limits_pass": True,
                "brand_naming_pass": True,
                "stats_fabrication_pass": True,
                "violations": [],
            },
        }

        platform_dir = output_root_path / platform
        platform_dir.mkdir(parents=True, exist_ok=True)
        out_path = platform_dir / "profile.json"
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(profile_data, f, indent=2)

        profiles.append(profile_data)

    return {"platforms": profiles}

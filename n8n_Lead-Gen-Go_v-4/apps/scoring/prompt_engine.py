"""
Ollama local inference integration.
Generates LLM reasoning summaries for ICP-scored leads.
Prompt templates are loaded from config/prompts/ via Jinja2 when available,
falling back to inline f-string prompts if Jinja2 is not installed.
"""

import json
import logging
import requests
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434/api/generate"

# Resolved at import time so modules using a different cwd still find templates
_PROMPTS_DIR = Path(__file__).resolve().parents[2] / "config" / "prompts"

CURRENT_SCORING_TEMPLATE = "scoring_v2"
CURRENT_REASONING_TEMPLATE = "reasoning_v2"

try:
    from jinja2 import Environment, FileSystemLoader, TemplateNotFound
    _JINJA_ENV = Environment(loader=FileSystemLoader(str(_PROMPTS_DIR)), trim_blocks=True, lstrip_blocks=True)
    HAS_JINJA2 = True
except ImportError:
    HAS_JINJA2 = False
    _JINJA_ENV = None

# Fallback inline prompts (used when Jinja2 is unavailable or template is missing)
_FALLBACK_SCORING_PROMPT = """\
You are an ICP (Ideal Customer Profile) analyst for a digital marketing agency targeting independent healthcare providers.

Analyze the following lead and provide a structured JSON assessment.

Lead Data:
- Business Name: {business_name}
- Category: {category}
- Website: {website}
- Website Status: {website_status}
- Booking System Present: {booking_present}
- SEO Quality: {seo_quality}
- Social Media Presence: {social_presence}
- ICP Score: {icp_score}/100 (higher = better fit / more opportunity)
- Risk Level: {risk_level}

Respond ONLY with valid JSON in this exact format:
{{
  "opportunity_summary": "2-3 sentence assessment of why this lead is or isn't a strong ICP fit",
  "top_pain_points": ["pain point 1", "pain point 2", "pain point 3"],
  "recommended_services": ["service 1", "service 2"],
  "outreach_angle": "specific angle for first contact with this practice",
  "confidence": "high|medium|low"
}}
"""

_FALLBACK_REASONING_PROMPT = """\
You are a senior sales strategist. Summarize in 2-3 sentences the outreach opportunity for this healthcare business:

Business: {business_name} ({category})
Location: {address}
Digital Gaps: {gaps}
ICP Score: {icp_score}/100

Be specific, actionable, and concise.
"""


def _render_template(template_name: str, context: dict) -> tuple[str, str]:
    """
    Render a Jinja2 template by name (without .j2 extension).
    Returns (rendered_text, version_used).
    Falls back to inline prompts on failure.
    """
    if HAS_JINJA2 and _JINJA_ENV:
        try:
            tmpl = _JINJA_ENV.get_template(f"{template_name}.j2")
            return tmpl.render(**context), template_name
        except Exception as e:
            log.debug("Jinja2 template '%s' failed: %s — using fallback", template_name, e)

    # Inline fallback
    if "scoring" in template_name:
        return _FALLBACK_SCORING_PROMPT.format(**context), f"{template_name}_fallback"
    return _FALLBACK_REASONING_PROMPT.format(**context), f"{template_name}_fallback"


def call_ollama(
    prompt: str,
    model: str = "qwen2.5-coder:7b",
    timeout: int = 60,
    stream: bool = False,
) -> Optional[str]:
    """Call Ollama API and return the generated text."""
    try:
        resp = requests.post(
            OLLAMA_URL,
            json={
                "model": model,
                "prompt": prompt,
                "stream": stream,
                "options": {
                    "temperature": 0.3,
                    "top_p": 0.9,
                    "num_predict": 512,
                },
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", "").strip()
    except requests.exceptions.ConnectionError:
        log.warning("Ollama not reachable at %s — is it running?", OLLAMA_URL)
        return None
    except Exception as e:
        log.warning("Ollama call failed: %s", e)
        return None


def is_ollama_available(model: str = "qwen2.5-coder:7b") -> bool:
    """Check if Ollama is running and the model is available."""
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        if resp.status_code == 200:
            tags = resp.json().get("models", [])
            available = [t.get("name", "") for t in tags]
            return any(model in m for m in available)
    except Exception:
        pass
    return False


def get_available_model(preferred: list[str]) -> Optional[str]:
    """Return first available model from preference list."""
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        if resp.status_code == 200:
            tags = resp.json().get("models", [])
            available = [t.get("name", "") for t in tags]
            for pref in preferred:
                if any(pref in m for m in available):
                    return pref
    except Exception:
        pass
    return None


def generate_scoring_analysis(
    lead: dict,
    score: dict,
    model: str = "qwen2.5-coder:7b",
    template: str = None,
) -> dict:
    """
    Generate structured ICP analysis via Ollama.
    Returns parsed JSON dict or a fallback dict if Ollama is unavailable.
    """
    enrichment = lead.get("enrichment") or {}
    flags = score.get("signal_flags", {})
    social_count = enrichment.get("social_count", flags.get("social_count", 0))
    has_booking = enrichment.get("booking_present", flags.get("booking_present", False))
    has_seo = enrichment.get("has_seo", flags.get("has_seo", False))

    template_name = template or CURRENT_SCORING_TEMPLATE
    context = {
        "business_name": lead.get("business_name", "Unknown"),
        "category": lead.get("category", "Unknown"),
        "website": lead.get("website", "N/A"),
        "website_status": enrichment.get("website_status", "unknown"),
        "booking_present": has_booking,
        "has_seo": has_seo,
        "social_count": social_count,
        "icp_score": score.get("icp_score", 0),
        "risk_level": score.get("risk_level", "unknown"),
        "gbp_rating": flags.get("gbp_rating"),
        "gbp_review_count": flags.get("gbp_review_count"),
        "gbp_unclaimed": flags.get("gbp_unclaimed", False),
        "pagespeed_performance": flags.get("pagespeed_performance"),
        # Fallback f-string keys
        "seo_quality": "Good" if has_seo else "Poor/Missing",
        "social_presence": f"{social_count} platforms" if social_count else "None detected",
    }

    prompt, version_used = _render_template(template_name, context)
    raw = call_ollama(prompt, model=model)
    if not raw:
        result = _fallback_analysis(lead, score)
        result["prompt_version"] = version_used
        return result

    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start != -1 and end > start:
            parsed = json.loads(raw[start:end])
            parsed["prompt_version"] = version_used
            return parsed
    except json.JSONDecodeError:
        pass

    return {"opportunity_summary": raw, "raw_response": True, "prompt_version": version_used}


def generate_reasoning_summary(
    lead: dict,
    score: dict,
    model: str = "llama3.1:8b",
    template: str = None,
) -> str:
    """Generate a brief natural-language outreach summary."""
    reasoning = score.get("reasoning", {})
    flags = score.get("signal_flags", {})
    gaps = []
    for key, val in reasoning.items():
        flag = val.get("flag", "")
        if "no_" in flag or "missing" in flag or "weak" in flag or "inaccessible" in flag or "unclaimed" in flag:
            gaps.append(flag.replace("_", " "))

    template_name = template or CURRENT_REASONING_TEMPLATE
    context = {
        "business_name": lead.get("business_name", "Unknown"),
        "category": lead.get("category", "Unknown"),
        "address": lead.get("address", "Unknown"),
        "gaps": ", ".join(gaps) if gaps else "minimal gaps detected",
        "icp_score": score.get("icp_score", 0),
        "gbp_unclaimed": flags.get("gbp_unclaimed", False),
        "pagespeed_performance": flags.get("pagespeed_performance"),
    }

    prompt, _ = _render_template(template_name, context)
    return call_ollama(prompt, model=model) or _fallback_summary(lead, score, gaps)


def _fallback_analysis(lead: dict, score: dict) -> dict:
    """Return deterministic fallback when Ollama is not available."""
    icp = score.get("icp_score", 0)
    gaps = []
    for key, val in score.get("reasoning", {}).items():
        flag = val.get("flag", "")
        if "no_" in flag or "missing" in flag or "weak" in flag:
            gaps.append(flag.replace("_", " ").title())

    if icp >= 70:
        summary = (
            f"{lead.get('business_name')} has significant digital gaps ({', '.join(gaps[:2])}), "
            "making them a strong ICP fit with high service need."
        )
    elif icp >= 40:
        summary = (
            f"{lead.get('business_name')} has moderate digital presence gaps. "
            "A targeted pitch around specific missing capabilities could convert."
        )
    else:
        summary = (
            f"{lead.get('business_name')} has solid digital infrastructure. "
            "Lower priority — may not need our services."
        )

    return {
        "opportunity_summary": summary,
        "top_pain_points": gaps[:3] if gaps else ["Limited digital presence"],
        "recommended_services": _recommend_services(score),
        "outreach_angle": _outreach_angle(score),
        "confidence": "medium",
        "generated_by": "deterministic_fallback",
    }


def _fallback_summary(lead: dict, score: dict, gaps: list) -> str:
    icp = score.get("icp_score", 0)
    name = lead.get("business_name", "This practice")
    if gaps:
        return f"{name} shows {', '.join(gaps[:2])}. With an ICP score of {icp}/100, this is a {'strong' if icp >= 70 else 'moderate'} outreach candidate."
    return f"{name} has an ICP score of {icp}/100. Digital presence is {'weak' if icp >= 50 else 'relatively strong'}."


def _recommend_services(score: dict) -> list[str]:
    services = []
    reasoning = score.get("reasoning", {})
    if reasoning.get("website", {}).get("flag") in ("missing_or_broken", "inaccessible"):
        services.append("Website rebuild / hosting")
    if reasoning.get("booking", {}).get("flag") == "no_booking":
        services.append("Online booking integration")
    if reasoning.get("seo", {}).get("flag") == "weak_seo":
        services.append("Local SEO optimization")
    if reasoning.get("social", {}).get("flag") in ("no_social", "minimal_social"):
        services.append("Social media setup & management")
    return services or ["Digital audit consultation"]


def _outreach_angle(score: dict) -> str:
    reasoning = score.get("reasoning", {})
    if reasoning.get("website", {}).get("flag") == "missing_or_broken":
        return "Lead with: 'We noticed your website may be having issues — we help local practices fix this fast.'"
    if reasoning.get("booking", {}).get("flag") == "no_booking":
        return "Lead with: 'Your competitors are getting 30% more appointments through online booking — here's how to catch up.'"
    if reasoning.get("seo", {}).get("flag") == "weak_seo":
        return "Lead with: 'Patients searching online can't find you easily — we can change that in 30 days.'"
    return "Lead with a digital presence audit offer specific to their category."

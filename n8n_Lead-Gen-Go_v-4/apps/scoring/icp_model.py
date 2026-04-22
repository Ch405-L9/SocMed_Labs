"""
Deterministic ICP scoring engine.
Produces a 0-100 risk/opportunity score based on enriched lead signals.
Higher score = higher opportunity (worse digital presence = better ICP fit).
"""

import json
import logging

log = logging.getLogger(__name__)

DEFAULT_WEIGHTS = {
    "website_missing": 30,
    "no_booking": 15,
    "weak_seo": 20,
    "no_social": 10,
    "independent_practice": 15,
    "strong_digital_maturity": -20,
    "poor_performance": 10,       # PageSpeed mobile score < 50
    "mediocre_performance": 5,    # PageSpeed mobile score 50-69
    "gbp_unclaimed": 10,          # No Google Business Profile or unclaimed listing
    "gbp_low_rating": 5,          # GBP rating below 3.5 stars
    "gbp_no_reviews": 5,          # 0 reviews on GBP
}

RISK_THRESHOLDS = {"high": 70, "medium": 40, "low": 0}

INDEPENDENT_SIGNALS = [
    "family practice", "family medicine", "chiropractic", "chiropractor",
    "dental", "dentist", "wellness", "physical therapy",
]

CHAIN_SIGNALS = [
    "northside", "wellstar", "emory", "piedmont", "kaiser",
    "cvs", "urgent care", "peachtree immediate",
]


def score_lead(lead: dict, weights: dict = None) -> dict:
    """
    Score a single enriched lead.

    Args:
        lead:    dict with optional 'enrichment' sub-dict from the crawler.
        weights: optional weight overrides (partial or full).

    Returns:
        dict with icp_score, risk_level, reasoning, signal_flags.
    """
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    enrichment = lead.get("enrichment") or _infer_enrichment_from_analysis(lead)

    status = enrichment.get("website_status", "unknown")
    has_booking = enrichment.get("booking_present", False)
    has_seo = enrichment.get("has_seo", False)
    social_count = enrichment.get("social_count", 0)
    perf_score = enrichment.get("pagespeed_performance")  # None if not fetched
    gbp_rating = enrichment.get("gbp_rating")             # None if not fetched
    gbp_review_count = enrichment.get("gbp_review_count") # None if not fetched
    gbp_unclaimed = enrichment.get("gbp_unclaimed", False)
    name_lower = (lead.get("business_name") or lead.get("name", "")).lower()
    category_lower = (lead.get("category", "")).lower()

    reasoning = {}
    raw_score = 0

    # Website reachability
    if status in ("dns_failed", "no_url", "exception", "connection_error"):
        reasoning["website"] = {"flag": "missing_or_broken", "points": w["website_missing"]}
        raw_score += w["website_missing"]
    elif status in ("blocked", "error_403", "timeout", "ssl_error"):
        reasoning["website"] = {"flag": "inaccessible", "points": round(w["website_missing"] * 0.7)}
        raw_score += round(w["website_missing"] * 0.7)
    elif status == "reachable":
        reasoning["website"] = {"flag": "reachable", "points": 0}
    else:
        reasoning["website"] = {"flag": status, "points": round(w["website_missing"] * 0.5)}
        raw_score += round(w["website_missing"] * 0.5)

    # Booking system
    if not has_booking:
        reasoning["booking"] = {"flag": "no_booking", "points": w["no_booking"]}
        raw_score += w["no_booking"]
    else:
        reasoning["booking"] = {"flag": "booking_present", "points": 0}

    # SEO quality
    if not has_seo:
        reasoning["seo"] = {"flag": "weak_seo", "points": w["weak_seo"]}
        raw_score += w["weak_seo"]
    else:
        reasoning["seo"] = {"flag": "seo_present", "points": 0}

    # Social presence
    if social_count == 0:
        reasoning["social"] = {"flag": "no_social", "points": w["no_social"]}
        raw_score += w["no_social"]
    elif social_count == 1:
        reasoning["social"] = {"flag": "minimal_social", "points": round(w["no_social"] * 0.5)}
        raw_score += round(w["no_social"] * 0.5)
    else:
        reasoning["social"] = {"flag": "social_present", "points": 0}

    # Independent practice bonus
    is_independent = any(sig in name_lower or sig in category_lower for sig in INDEPENDENT_SIGNALS)
    is_chain = any(sig in name_lower for sig in CHAIN_SIGNALS)
    if is_independent and not is_chain:
        reasoning["practice_type"] = {"flag": "independent_practice", "points": w["independent_practice"]}
        raw_score += w["independent_practice"]
    else:
        reasoning["practice_type"] = {"flag": "chain_or_unknown", "points": 0}

    # Strong digital maturity penalty
    if has_booking and has_seo and social_count >= 2:
        reasoning["digital_maturity"] = {"flag": "strong_digital", "points": w["strong_digital_maturity"]}
        raw_score += w["strong_digital_maturity"]
    else:
        reasoning["digital_maturity"] = {"flag": "weak_digital", "points": 0}

    # Google Business Profile signals (only scored when GBP lookup ran)
    if gbp_unclaimed:
        reasoning["gbp"] = {"flag": "gbp_unclaimed", "points": w["gbp_unclaimed"]}
        raw_score += w["gbp_unclaimed"]
    elif gbp_review_count is not None or gbp_rating is not None:
        gbp_pts = 0
        gbp_flag = "gbp_present"
        if gbp_review_count is not None and gbp_review_count == 0:
            gbp_pts += w["gbp_no_reviews"]
            gbp_flag = "gbp_no_reviews"
        if gbp_rating is not None and gbp_rating < 3.5:
            gbp_pts += w["gbp_low_rating"]
            gbp_flag = "gbp_low_rating" if gbp_pts else gbp_flag
        reasoning["gbp"] = {
            "flag": gbp_flag,
            "rating": gbp_rating,
            "review_count": gbp_review_count,
            "points": gbp_pts,
        }
        raw_score += gbp_pts
    else:
        reasoning["gbp"] = {"flag": "gbp_not_checked", "points": 0}

    # PageSpeed performance (only scored when data is present)
    if perf_score is not None:
        if perf_score < 50:
            pts = w["poor_performance"]
            reasoning["performance"] = {"flag": "poor_performance", "score": perf_score, "points": pts}
            raw_score += pts
        elif perf_score < 70:
            pts = w["mediocre_performance"]
            reasoning["performance"] = {"flag": "mediocre_performance", "score": perf_score, "points": pts}
            raw_score += pts
        else:
            reasoning["performance"] = {"flag": "acceptable_performance", "score": perf_score, "points": 0}
    else:
        reasoning["performance"] = {"flag": "not_measured", "points": 0}

    icp_score = max(0, min(100, raw_score))

    if icp_score >= RISK_THRESHOLDS["high"]:
        risk_level = "high"
    elif icp_score >= RISK_THRESHOLDS["medium"]:
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "icp_score": icp_score,
        "risk_level": risk_level,
        "reasoning": reasoning,
        "signal_flags": {
            "website_status": status,
            "booking_present": has_booking,
            "has_seo": has_seo,
            "social_count": social_count,
            "is_independent": is_independent,
            "pagespeed_performance": perf_score,
            "gbp_rating": gbp_rating,
            "gbp_review_count": gbp_review_count,
            "gbp_unclaimed": gbp_unclaimed,
        },
    }


def _infer_enrichment_from_analysis(lead: dict) -> dict:
    """
    Convert analyzed_leads.json 'analysis' field to enrichment format.
    Used when scoring pre-existing data without a full re-crawl.
    """
    analysis = lead.get("analysis", {})
    status = analysis.get("status", "unknown")

    if status == "success":
        website_status = "reachable"
    elif status == "error":
        code = analysis.get("code", 0)
        website_status = "blocked" if code == 403 else "not_found" if code == 404 else f"error_{code}"
    elif status == "exception":
        err = analysis.get("error", "")
        website_status = "dns_failed" if ("NameResolution" in err or "Name or service not known" in err) else "connection_error"
    else:
        website_status = status

    socials = analysis.get("socials", [])
    return {
        "website_status": website_status,
        "booking_present": analysis.get("booking", False),
        "has_seo": analysis.get("has_seo", False),
        "social_links": socials,
        "social_count": len(socials),
        "seo_title": analysis.get("title"),
        "is_https": analysis.get("secure", False),
        "pagespeed_performance": None,
        "pagespeed_seo": None,
        "pagespeed_accessibility": None,
        "gbp_rating": None,
        "gbp_review_count": None,
        "gbp_photo_count": None,
        "gbp_verified": False,
        "gbp_unclaimed": False,
    }


def score_all_leads(leads: list[dict], weights: dict = None) -> list[dict]:
    """Score a list of leads. Returns leads sorted by icp_score descending."""
    scored = []
    for lead in leads:
        s = score_lead(lead, weights)
        scored.append({**lead, "score": s})
    scored.sort(key=lambda x: x["score"]["icp_score"], reverse=True)
    return scored

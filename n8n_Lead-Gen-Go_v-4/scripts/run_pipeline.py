#!/usr/bin/env python3
"""
Main pipeline orchestrator.
Runs the full ICP lead generation pipeline end-to-end or step-by-step.

Usage:
  python run_pipeline.py                                  # full pipeline
  python run_pipeline.py import --file leads.csv          # import CSV leads
  python run_pipeline.py collect --zip 30350              # single-ZIP collect
  python run_pipeline.py collect --zips 30350,30342,30328 # multi-ZIP collect
  python run_pipeline.py collect --center 30350 --radius 10  # radius collect
  python run_pipeline.py crawl                            # incremental crawl
  python run_pipeline.py crawl --force-crawl              # bypass cache
  python run_pipeline.py crawl --gbp                      # with GBP signals
  python run_pipeline.py crawl --playwright               # retry blocked sites with browser
  python run_pipeline.py score                            # score only
  python run_pipeline.py score --ollama                   # score + LLM enrichment
  python run_pipeline.py export                           # export CSV from DB
  python run_pipeline.py viz                              # generate charts
  python run_pipeline.py calibrate                        # tune weights from human overrides
  python run_pipeline.py deduplicate                      # merge near-duplicate leads
"""

import sys
import json
import argparse
import logging
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "apps" / "collector"))
sys.path.insert(0, str(ROOT / "apps" / "crawler"))
sys.path.insert(0, str(ROOT / "apps" / "scoring"))
sys.path.insert(0, str(ROOT / "apps" / "storage"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(ROOT / "data" / "pipeline.log"),
    ],
)
log = logging.getLogger(__name__)


_CSV_COLUMN_MAP = {
    # business name variants
    "business name": "business_name",
    "businessname":  "business_name",
    "name":          "business_name",
    "company":       "business_name",
    "company name":  "business_name",
    # website variants
    "website url":   "website",
    "website":       "website",
    "url":           "website",
    "site":          "website",
    "web":           "website",
    # category
    "category":      "category",
    "type":          "category",
    "business type": "category",
    # address
    "full address":  "address",
    "address":       "address",
    "street":        "address",
    "location":      "address",
    # geo_area / zip
    "geo area":      "geo_area",
    "geo_area":      "geo_area",
    "zip":           "geo_area",
    "zip code":      "geo_area",
    "zipcode":       "geo_area",
    "city":          "geo_area",
    # phone
    "phone":         "phone",
    "phone number":  "phone",
    "telephone":     "phone",
    # email
    "email":         "email",
    "email address": "email",
}


def step_import(file_path: str, geo_area: str = None, category: str = None) -> list[dict]:
    """Import leads from a CSV file into raw_leads.json, deduplicating against existing entries."""
    import csv as csv_mod

    log.info("=== STEP: IMPORT ===")
    csv_path = Path(file_path)
    if not csv_path.exists():
        log.error("CSV file not found: %s", csv_path)
        return []

    raw_leads_path = ROOT / "data" / "raw_leads.json"
    existing = []
    if raw_leads_path.exists():
        with open(raw_leads_path) as f:
            try:
                existing = json.load(f)
            except json.JSONDecodeError:
                existing = []

    existing_names = {(l.get("business_name") or "").lower() for l in existing}
    existing_websites = {(l.get("website") or "").lower().rstrip("/") for l in existing if l.get("website")}

    imported = []
    skipped = 0

    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv_mod.DictReader(f)
        if reader.fieldnames is None:
            log.error("CSV file appears empty or has no headers.")
            return []

        # Build column name → canonical name mapping
        col_map = {}
        for raw_col in reader.fieldnames:
            normalized = raw_col.strip().lower()
            if normalized in _CSV_COLUMN_MAP:
                col_map[raw_col] = _CSV_COLUMN_MAP[normalized]

        log.info("CSV columns detected: %s", list(reader.fieldnames))
        log.info("Column mapping: %s", col_map)

        for row in reader:
            lead = {}
            for raw_col, canonical in col_map.items():
                val = (row.get(raw_col) or "").strip()
                if val:
                    lead[canonical] = val

            if not lead.get("business_name"):
                skipped += 1
                continue

            # Apply defaults from CLI args
            if geo_area and not lead.get("geo_area"):
                lead["geo_area"] = geo_area
            if category and not lead.get("category"):
                lead["category"] = category

            # Deduplicate by name or website
            name_key = lead.get("business_name", "").lower()
            website_key = (lead.get("website") or "").lower().rstrip("/")

            if name_key in existing_names:
                skipped += 1
                continue
            if website_key and website_key in existing_websites:
                skipped += 1
                continue

            existing_names.add(name_key)
            if website_key:
                existing_websites.add(website_key)

            imported.append(lead)

    all_leads = existing + imported
    raw_leads_path.parent.mkdir(exist_ok=True)
    with open(raw_leads_path, "w") as f:
        json.dump(all_leads, f, indent=2)

    log.info("Import complete: %d new leads added, %d skipped (duplicates/invalid)", len(imported), skipped)
    log.info("Total leads in raw_leads.json: %d", len(all_leads))

    if imported:
        log.info("Sample imported leads:")
        for lead in imported[:3]:
            log.info("  - %s | %s | %s", lead.get("business_name"), lead.get("website", "no url"), lead.get("address", ""))

    return all_leads


def _load_zip_centroids() -> dict:
    """Load ZIP centroid data from config/zcta_centroids.csv."""
    import csv as csv_mod
    path = ROOT / "config" / "zcta_centroids.csv"
    if not path.exists():
        return {}
    centroids = {}
    with open(path) as f:
        for row in csv_mod.DictReader(f):
            try:
                centroids[row["zip"]] = (float(row["lat"]), float(row["lon"]))
            except (ValueError, KeyError):
                pass
    return centroids


def _haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    import math
    R = 3958.8
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def find_zips_within_radius(center_zip: str, radius_miles: float) -> list[str]:
    centroids = _load_zip_centroids()
    if center_zip not in centroids:
        log.warning("ZIP %s not found in centroids data — using it alone", center_zip)
        return [center_zip]
    clat, clon = centroids[center_zip]
    result = [
        z for z, (lat, lon) in centroids.items()
        if _haversine_miles(clat, clon, lat, lon) <= radius_miles
    ]
    log.info("Found %d ZIPs within %.1f miles of %s", len(result), radius_miles, center_zip)
    return sorted(result)


def step_collect(
    zip_codes: list[str],
    category: str,
    max_results: int = 10,
    pause: float = 2.0,
) -> list[dict]:
    from search import collect_leads
    log.info("=== STEP 1: COLLECT ===")

    out_path = ROOT / "data" / "raw_leads.json"
    existing = []
    if out_path.exists():
        with open(out_path) as f:
            try:
                existing = json.load(f)
            except json.JSONDecodeError:
                existing = []

    existing_urls = {(l.get("website") or "").lower().rstrip("/") for l in existing}
    existing_names = {(l.get("business_name") or "").lower() for l in existing}

    all_new = []
    seen_this_run: set[str] = set()

    for zip_code in zip_codes:
        log.info("Collecting for ZIP %s — %s ...", zip_code, category)
        leads = collect_leads(zip_code=zip_code, category=category, max_per_query=max_results, pause=pause)

        for lead in leads:
            url_key = (lead.get("website") or "").lower().rstrip("/")
            name_key = (lead.get("business_name") or "").lower()

            if url_key in existing_urls or name_key in existing_names:
                continue
            if url_key in seen_this_run:
                continue

            if not lead.get("geo_area"):
                lead["geo_area"] = f"ZIP {zip_code}"
            if url_key:
                seen_this_run.add(url_key)
            existing_urls.add(url_key)
            existing_names.add(name_key)
            all_new.append(lead)

    combined = existing + all_new
    all_leads, deduped = deduplicate_leads(combined)
    if deduped:
        log.info("Deduplication removed %d near-duplicate leads", deduped)

    out_path.parent.mkdir(exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(all_leads, f, indent=2)

    log.info(
        "Collected %d total leads (%d new across %d ZIP(s)) → %s",
        len(all_leads), len(all_new), len(zip_codes), out_path,
    )
    return all_leads


def step_crawl(
    leads: list[dict] = None,
    timeout: int = 10,
    pause: float = 1.0,
    force_crawl: bool = False,
    crawl_window_days: int = 7,
    use_gbp: bool = False,
    gbp_pause: float = 2.0,
    extract_contacts: bool = True,
    use_pagespeed: bool = False,
    pagespeed_api_key: str = "",
    use_playwright: bool = False,
) -> list[dict]:
    from fetch import enrich_leads
    log.info("=== STEP 2: CRAWL ===")

    if leads is None:
        raw_path = ROOT / "data" / "raw_leads.json"
        if not raw_path.exists():
            analyzed = ROOT / "data" / "analyzed_leads.json"
            if analyzed.exists():
                log.info("Using existing analyzed_leads.json")
                raw_path = analyzed
            else:
                log.error("No leads file found. Run 'collect' first.")
                return []
        with open(raw_path) as f:
            leads = json.load(f)

    # Normalize name/url fields
    for lead in leads:
        if "name" in lead and "business_name" not in lead:
            lead["business_name"] = lead.pop("name")
        if "url" in lead and "website" not in lead:
            lead["website"] = lead.pop("url")

    # Build incremental cache from existing enriched_leads.json
    crawl_cache = {}
    if not force_crawl:
        existing_enriched = ROOT / "data" / "enriched_leads.json"
        if existing_enriched.exists():
            try:
                with open(existing_enriched) as f:
                    prev = json.load(f)
                for lead in prev:
                    url = lead.get("website") or lead.get("url")
                    enrichment = lead.get("enrichment") or {}
                    if url and enrichment.get("last_crawled"):
                        crawl_cache[url] = {
                            "last_crawled": enrichment["last_crawled"],
                            "content_hash": enrichment.get("content_hash"),
                        }
                        # Carry previous enrichment into the current lead list
                        for curr in leads:
                            if (curr.get("website") or curr.get("url")) == url and not curr.get("enrichment"):
                                curr["enrichment"] = enrichment
                log.info("Loaded %d cached crawl timestamps for incremental mode", len(crawl_cache))
            except (json.JSONDecodeError, Exception) as e:
                log.warning("Could not load crawl cache: %s", e)

    enriched = enrich_leads(
        leads,
        timeout=timeout,
        pause=pause,
        extract_contacts=extract_contacts,
        use_pagespeed=use_pagespeed,
        pagespeed_api_key=pagespeed_api_key,
        crawl_cache=crawl_cache,
        crawl_window_days=crawl_window_days,
        force_crawl=force_crawl,
        use_playwright=use_playwright,
    )

    # Optional: GBP signal enrichment
    if use_gbp:
        log.info("=== STEP 2b: GBP SIGNALS ===")
        sys.path.insert(0, str(ROOT / "apps" / "collector"))
        from gbp import enrich_leads_gbp
        enriched = enrich_leads_gbp(enriched, pause=gbp_pause)

    out_path = ROOT / "data" / "enriched_leads.json"
    with open(out_path, "w") as f:
        json.dump(enriched, f, indent=2)

    log.info("Enriched %d leads → %s", len(enriched), out_path)
    return enriched


def step_score(leads: list[dict] = None, use_ollama: bool = False) -> list[dict]:
    from icp_model import score_all_leads
    log.info("=== STEP 3: SCORE ===")

    if leads is None:
        # Try enriched → raw → analyzed
        for fname in ["enriched_leads.json", "raw_leads.json", "analyzed_leads.json"]:
            path = ROOT / "data" / fname
            if path.exists():
                with open(path) as f:
                    leads = json.load(f)
                log.info("Loaded leads from %s", path)
                break

    if not leads:
        log.error("No leads to score.")
        return []

    scored = score_all_leads(leads)

    if use_ollama:
        scored = _enrich_with_ollama(scored)

    out_path = ROOT / "data" / "scored_leads_full.json"
    with open(out_path, "w") as f:
        json.dump(scored, f, indent=2)

    log.info("Scored %d leads → %s", len(scored), out_path)

    # Print quick summary
    high = sum(1 for l in scored if l["score"]["icp_score"] >= 70)
    med = sum(1 for l in scored if 40 <= l["score"]["icp_score"] < 70)
    low = sum(1 for l in scored if l["score"]["icp_score"] < 40)
    log.info("Score summary — High: %d | Medium: %d | Low: %d", high, med, low)

    return scored


def _enrich_with_ollama(scored: list[dict]) -> list[dict]:
    from prompt_engine import (
        get_available_model, generate_scoring_analysis,
        generate_reasoning_summary
    )

    model_prefs = ["qwen2.5-coder:7b", "llama3.1:8b", "llama3.2:3b", "phi3:mini"]
    scoring_model = get_available_model(model_prefs)
    reasoning_model = get_available_model(["llama3.1:8b", "llama3.2:3b", "qwen2.5-coder:7b", "phi3:mini"])

    if not scoring_model:
        log.warning("No Ollama models available — skipping LLM enrichment")
        return scored

    log.info("Using Ollama models: scoring=%s reasoning=%s", scoring_model, reasoning_model)

    for i, lead in enumerate(scored, 1):
        score = lead.get("score", {})
        icp = score.get("icp_score", 0)
        if icp < 30:
            continue  # Skip low-opportunity leads to save inference time

        log.info("[%d/%d] LLM enriching: %s (score=%d)", i, len(scored),
                 lead.get("business_name"), icp)

        analysis = generate_scoring_analysis(lead, score, model=scoring_model)
        summary = generate_reasoning_summary(lead, score, model=reasoning_model or scoring_model)

        lead["score"]["ollama_analysis"] = analysis
        lead["score"]["ollama_summary"] = summary
        lead["score"]["model_used"] = scoring_model

    return scored


def step_export(db_path: str = None) -> str:
    from db import get_conn, init_db, export_csv, get_all_leads_full

    log.info("=== STEP 4: EXPORT ===")
    db = db_path or str(ROOT / "data" / "leads.db")

    if not Path(db).exists():
        log.warning("No SQLite DB found at %s — exporting from JSON instead", db)
        return _export_from_json()

    conn = get_conn(db)
    csv_path = str(ROOT / "data" / "scored_leads.csv")
    export_csv(conn, csv_path)
    conn.close()
    log.info("Exported → %s", csv_path)
    return csv_path


def _export_from_json() -> str:
    """Export directly from scored JSON when no DB exists."""
    import csv as csv_mod
    json_path = ROOT / "data" / "scored_leads_full.json"
    if not json_path.exists():
        log.error("scored_leads_full.json not found.")
        return ""

    with open(json_path) as f:
        leads = json.load(f)

    csv_path = ROOT / "data" / "scored_leads.csv"
    fieldnames = [
        "business_name", "website", "category", "geo_area", "address",
        "website_status", "booking_present", "has_seo", "social_count",
        "icp_score", "risk_level", "final_score", "human_verified", "human_notes"
    ]

    with open(csv_path, "w", newline="") as f:
        writer = csv_mod.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for lead in leads:
            score = lead.get("score", {})
            enrichment = lead.get("enrichment") or {}
            row = {
                "business_name": lead.get("business_name"),
                "website": lead.get("website") or lead.get("url"),
                "category": lead.get("category"),
                "geo_area": lead.get("geo_area", "ZIP 30350"),
                "address": lead.get("address"),
                "website_status": enrichment.get("website_status", "unknown"),
                "booking_present": enrichment.get("booking_present", False),
                "has_seo": enrichment.get("has_seo", False),
                "social_count": enrichment.get("social_count", 0),
                "icp_score": score.get("icp_score"),
                "risk_level": score.get("risk_level"),
                "final_score": score.get("icp_score"),
                "human_verified": False,
                "human_notes": "",
            }
            writer.writerow(row)

    log.info("Exported %d leads → %s", len(leads), csv_path)
    return str(csv_path)


def step_viz():
    import subprocess
    log.info("=== STEP 5: VISUALIZE ===")
    viz_script = ROOT / "viz" / "dashboard.py"
    result = subprocess.run(
        [sys.executable, str(viz_script)],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        log.info("Dashboard generated successfully")
        print(result.stdout)
    else:
        log.error("Dashboard error: %s", result.stderr)


# ---------------------------------------------------------------------------
# 3.5 Lead Deduplication
# ---------------------------------------------------------------------------

def _similarity(a: str, b: str) -> float:
    from difflib import SequenceMatcher
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def deduplicate_leads(leads: list[dict], name_threshold: float = 0.85) -> list[dict]:
    """
    Remove near-duplicate leads using fuzzy name matching + address prefix.
    Two leads are considered duplicates if:
      - Name similarity > name_threshold AND
      - First 25 chars of address match (same block / suite cluster)
    OR
      - Exact same website URL (normalized)
    """
    seen: list[dict] = []
    seen_urls: set[str] = set()
    removed = 0

    for lead in leads:
        name = lead.get("business_name", "") or ""
        addr = (lead.get("address", "") or "")[:25]
        url = (lead.get("website", "") or "").lower().rstrip("/")

        # URL dedup (exact)
        if url and url in seen_urls:
            log.debug("Dedup (url match): %s", name)
            removed += 1
            continue

        # Fuzzy name + address dedup
        is_dup = any(
            _similarity(name, s.get("business_name", "")) > name_threshold
            and addr == (s.get("address", "") or "")[:25]
            for s in seen
        )
        if is_dup:
            log.debug("Dedup (name/addr match): %s", name)
            removed += 1
            continue

        seen.append(lead)
        if url:
            seen_urls.add(url)

    return seen, removed


def step_deduplicate() -> list[dict]:
    """Load raw_leads.json, remove duplicates, write back."""
    log.info("=== STEP: DEDUPLICATE ===")
    raw_path = ROOT / "data" / "raw_leads.json"
    if not raw_path.exists():
        log.error("raw_leads.json not found.")
        return []

    with open(raw_path) as f:
        leads = json.load(f)

    before = len(leads)
    cleaned, removed = deduplicate_leads(leads)

    with open(raw_path, "w") as f:
        json.dump(cleaned, f, indent=2)

    log.info("Deduplication: %d leads → %d kept, %d removed", before, len(cleaned), removed)
    print(f"\nDeduplication complete: {before} → {len(cleaned)} leads ({removed} removed)")
    return cleaned


# ---------------------------------------------------------------------------
# 3.1 Weight Calibration from Human Overrides
# ---------------------------------------------------------------------------

_REASONING_KEY_TO_WEIGHT = {
    "website":        {"missing_or_broken": "website_missing", "inaccessible": "website_missing"},
    "booking":        {"no_booking": "no_booking"},
    "seo":            {"weak_seo": "weak_seo"},
    "social":         {"no_social": "no_social", "minimal_social": "no_social"},
    "practice_type":  {"independent_practice": "independent_practice"},
    "digital_maturity": {"strong_digital": "strong_digital_maturity"},
    "gbp":            {"gbp_unclaimed": "gbp_unclaimed", "gbp_no_reviews": "gbp_no_reviews",
                       "gbp_low_rating": "gbp_low_rating"},
    "performance":    {"poor_performance": "poor_performance", "mediocre_performance": "mediocre_performance"},
}


def step_calibrate(min_overrides: int = 5, db_path: str = None) -> dict:
    """
    Analyze human score overrides and suggest adjusted ICP weights.

    Algorithm:
      For each signal that fired in overridden leads, compute the average
      (human_score - model_score) delta. Signals consistently over-scored
      by the model get their weight reduced proportionally; under-scored
      signals get an increase. Requires at least min_overrides data points.

    Writes suggested weights to data/calibrated_weights.json and prints a report.
    """
    from db import get_conn, get_human_overrides
    from icp_model import DEFAULT_WEIGHTS
    from collections import defaultdict

    log.info("=== STEP: CALIBRATE ===")
    db = db_path or str(ROOT / "data" / "leads.db")

    if not Path(db).exists():
        log.error("Database not found: %s", db)
        return {}

    conn = get_conn(db)
    overrides = get_human_overrides(conn)
    conn.close()

    if len(overrides) < min_overrides:
        print(f"\nCalibration requires at least {min_overrides} human overrides.")
        print(f"Currently have {len(overrides)}. Continue reviewing leads to accumulate more data.")
        return {}

    # For each signal, collect deltas (human - model) where that signal fired
    signal_deltas: dict[str, list[float]] = defaultdict(list)
    global_delta_sum = 0.0

    for row in overrides:
        model_score = row["icp_score"] or 0
        human_score = row["override_score"] or 0
        delta = human_score - model_score
        global_delta_sum += delta

        reasoning = {}
        try:
            reasoning = json.loads(row["reasoning"]) if row["reasoning"] else {}
        except Exception:
            pass

        for reasoning_key, signal_data in reasoning.items():
            flag = signal_data.get("flag", "")
            points = signal_data.get("points", 0)
            if points == 0:
                continue  # Signal didn't fire — skip

            weight_key = None
            key_map = _REASONING_KEY_TO_WEIGHT.get(reasoning_key, {})
            for flag_pattern, wk in key_map.items():
                if flag_pattern in flag:
                    weight_key = wk
                    break

            if weight_key:
                signal_deltas[weight_key].append(delta)

    avg_global_delta = global_delta_sum / len(overrides)

    # Build adjusted weights
    current_weights = dict(DEFAULT_WEIGHTS)
    adjustments: dict[str, dict] = {}

    MIN_SAMPLES = 3  # Minimum signal occurrences to adjust

    for weight_key, deltas in signal_deltas.items():
        if len(deltas) < MIN_SAMPLES:
            continue
        avg_delta = sum(deltas) / len(deltas)
        current_w = current_weights.get(weight_key, 0)
        if current_w == 0:
            continue

        # Adjustment factor: if humans score 10% lower when this signal fires,
        # reduce the weight by 10%
        # Cap adjustment at ±40% per calibration run
        factor = max(0.6, min(1.4, 1.0 + avg_delta / max(abs(current_w), 1) * 0.5))
        new_w = round(current_w * factor, 1)

        adjustments[weight_key] = {
            "current": current_w,
            "suggested": new_w,
            "avg_human_delta": round(avg_delta, 1),
            "sample_count": len(deltas),
            "direction": "reduced" if new_w < current_w else "increased",
        }

    suggested_weights = dict(current_weights)
    for wk, adj in adjustments.items():
        suggested_weights[wk] = adj["suggested"]

    # Write calibrated weights
    out = {
        "generated_from_overrides": len(overrides),
        "avg_global_delta": round(avg_global_delta, 2),
        "original_weights": current_weights,
        "suggested_weights": suggested_weights,
        "adjustments": adjustments,
    }
    out_path = ROOT / "data" / "calibrated_weights.json"
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)

    # Print report
    print(f"\nCalibration Report ({len(overrides)} human overrides)")
    print(f"Average human adjustment: {avg_global_delta:+.1f} points (model tends to "
          f"{'over' if avg_global_delta < 0 else 'under'}-score)")
    print(f"\n{'Signal':<28} {'Current':>8} {'Suggested':>10} {'Avg Delta':>10} {'Samples':>8}")
    print("─" * 70)
    for wk, adj in sorted(adjustments.items(), key=lambda x: abs(x[1]["avg_human_delta"]), reverse=True):
        arrow = "↓" if adj["suggested"] < adj["current"] else "↑"
        print(f"{wk:<28} {adj['current']:>8.1f} {adj['suggested']:>10.1f} "
              f"{adj['avg_human_delta']:>+10.1f} {adj['sample_count']:>8}  {arrow}")

    if not adjustments:
        print("  No signals had enough samples for adjustment (need ≥3 per signal).")

    print(f"\nSuggested weights written to: {out_path}")
    print("To apply: copy 'suggested_weights' values into config/config.yaml → scoring.weights")
    print("          and into DEFAULT_WEIGHTS in apps/scoring/icp_model.py")

    return suggested_weights


def main():
    parser = argparse.ArgumentParser(description="ICP Lead Generation Pipeline")
    parser.add_argument("step", nargs="?", default="all",
                        choices=["all", "import", "collect", "crawl", "score", "export",
                                 "viz", "calibrate", "deduplicate"],
                        help="Pipeline step to run")

    # Collection flags
    parser.add_argument("--zip", default="30350", help="Single ZIP code to collect")
    parser.add_argument("--zips", default=None, help="Comma-separated list of ZIP codes")
    parser.add_argument("--center", default=None, metavar="ZIP", help="Center ZIP for radius search")
    parser.add_argument("--radius", type=float, default=10.0, metavar="MILES",
                        help="Search radius in miles (used with --center)")
    parser.add_argument("--category", default="healthcare")
    parser.add_argument("--max", type=int, default=10, help="Max results per search query per ZIP")

    # Crawl flags
    parser.add_argument("--timeout", type=int, default=10, help="HTTP timeout for crawler")
    parser.add_argument("--pause", type=float, default=1.5, help="Pause between requests")
    parser.add_argument("--no-crawl", action="store_true", help="Skip crawling, use existing data")
    parser.add_argument("--force-crawl", dest="force_crawl", action="store_true",
                        help="Re-crawl all sites regardless of crawl cache")
    parser.add_argument("--crawl-window", dest="crawl_window", type=int, default=7,
                        help="Days before re-crawling a site (0 = always crawl)")
    parser.add_argument("--gbp", action="store_true", help="Fetch Google Business Profile signals")
    parser.add_argument("--gbp-pause", dest="gbp_pause", type=float, default=2.5,
                        help="Pause between GBP lookups")
    parser.add_argument("--no-contacts", dest="no_contacts", action="store_true",
                        help="Skip phone and email extraction")
    parser.add_argument("--pagespeed", action="store_true", help="Call PageSpeed Insights API")
    parser.add_argument("--pagespeed-key", dest="pagespeed_key", default="",
                        help="Google API key for PageSpeed")
    parser.add_argument("--playwright", action="store_true",
                        help="Retry blocked (403) sites using Playwright headless browser")

    # Calibration flags
    parser.add_argument("--min-overrides", dest="min_overrides", type=int, default=5,
                        help="Minimum human overrides required for calibration (default: 5)")

    # Score / LLM flags
    parser.add_argument("--ollama", action="store_true", help="Use Ollama for LLM enrichment")
    parser.add_argument("--prompt-template", dest="prompt_template", default=None,
                        help="Jinja2 template name to use (e.g. scoring_v2)")

    # Import flags
    parser.add_argument("--file", dest="import_file", metavar="PATH",
                        help="CSV file to import (used with 'import' step)")
    parser.add_argument("--geo-area", dest="geo_area", help="Default geo area for imported leads")

    args = parser.parse_args()

    # Create data dir
    (ROOT / "data").mkdir(exist_ok=True)

    start = time.time()

    # Resolve ZIP list
    if args.center:
        zip_codes = find_zips_within_radius(args.center, args.radius)
    elif args.zips:
        zip_codes = [z.strip() for z in args.zips.split(",") if z.strip()]
    else:
        zip_codes = [args.zip]

    if args.step == "calibrate":
        step_calibrate(min_overrides=args.min_overrides)
        return

    if args.step == "deduplicate":
        step_deduplicate()
        return

    if args.step == "import":
        if not args.import_file:
            parser.error("'import' step requires --file PATH")
        step_import(args.import_file, geo_area=args.geo_area, category=args.category)
        print(f"\nImport complete. Next: python scripts/run_pipeline.py crawl")
        return

    if args.step in ("all", "collect"):
        leads = step_collect(zip_codes, args.category, args.max, args.pause)
        if args.step == "collect":
            return

    if args.step in ("all", "crawl") and not args.no_crawl:
        enriched = step_crawl(
            timeout=args.timeout,
            pause=args.pause,
            force_crawl=args.force_crawl,
            crawl_window_days=args.crawl_window,
            use_gbp=args.gbp,
            gbp_pause=args.gbp_pause,
            extract_contacts=not args.no_contacts,
            use_pagespeed=args.pagespeed,
            pagespeed_api_key=args.pagespeed_key,
            use_playwright=args.playwright,
        )
        if args.step == "crawl":
            return

    if args.step in ("all", "score"):
        scored = step_score(use_ollama=args.ollama)
        if args.step == "score":
            return

    if args.step in ("all", "export"):
        step_export()
        if args.step == "export":
            return

    if args.step in ("all", "viz"):
        step_viz()

    elapsed = time.time() - start
    log.info("Pipeline complete in %.1fs", elapsed)
    print(f"\nPipeline done in {elapsed:.1f}s")
    print(f"Next: python apps/human_loop/review_cli.py --input data/scored_leads_full.json")


if __name__ == "__main__":
    main()

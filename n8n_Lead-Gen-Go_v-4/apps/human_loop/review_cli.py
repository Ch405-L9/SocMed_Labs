#!/usr/bin/env python3
"""
Human-in-the-Loop CLI review tool.
Presents each scored lead for human approval, modification, or rejection.
Stores decisions to SQLite and exports final CSV.
"""

import sys
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "storage"))
sys.path.insert(0, str(ROOT / "apps" / "scoring"))

from db import get_conn, init_db, upsert_lead, upsert_enrichment, upsert_score, upsert_human_review, export_csv, get_pending_review

logging.basicConfig(level=logging.WARNING)

RESET  = "\033[0m"
BOLD   = "\033[1m"
CYAN   = "\033[96m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
GRAY   = "\033[90m"
BLUE   = "\033[94m"


def color_score(score: int) -> str:
    if score >= 70:
        return f"{RED}{BOLD}{score}{RESET}"
    elif score >= 40:
        return f"{YELLOW}{score}{RESET}"
    return f"{GREEN}{score}{RESET}"


def color_risk(risk: str) -> str:
    mapping = {"high": RED, "medium": YELLOW, "low": GREEN}
    c = mapping.get(risk, GRAY)
    return f"{c}{BOLD}{risk.upper()}{RESET}"


def render_lead(lead: dict, idx: int, total: int):
    score_data = lead.get("score", {})
    enrichment = lead.get("enrichment") or lead.get("analysis") or {}
    icp = score_data.get("icp_score", "?")
    risk = score_data.get("risk_level", "unknown")
    reasoning = score_data.get("reasoning", {})
    llm = score_data.get("ollama_summary") or lead.get("ollama_summary")
    llm_analysis = score_data.get("ollama_analysis") or {}

    print(f"\n{'='*70}")
    print(f"{BOLD}{CYAN}Lead {idx}/{total}{RESET}")
    print(f"{'='*70}")
    print(f"  {BOLD}Business:{RESET} {lead.get('business_name', 'N/A')}")
    print(f"  {BOLD}Category:{RESET} {lead.get('category', 'N/A')}")
    print(f"  {BOLD}Address: {RESET} {lead.get('address', 'N/A')}")
    print(f"  {BOLD}Website: {RESET} {lead.get('website') or lead.get('url', 'N/A')}")
    print(f"\n  {BOLD}--- Digital Presence Signals ---{RESET}")

    # Enrichment signals
    status = enrichment.get("website_status") or _infer_status(enrichment)
    booking = enrichment.get("booking_present") or enrichment.get("booking", False)
    has_seo = enrichment.get("has_seo", False)
    socials = enrichment.get("social_links") or enrichment.get("socials", [])

    status_color = GREEN if status == "reachable" else RED
    print(f"  Website Status:  {status_color}{status}{RESET}")
    print(f"  Booking System:  {'✓' if booking else '✗'} {'Present' if booking else 'Not Found'}")
    print(f"  SEO Quality:     {'✓' if has_seo else '✗'} {'Good' if has_seo else 'Weak/Missing'}")
    print(f"  Social Presence: {'✓' if socials else '✗'} {len(socials)} platform(s)")
    if socials:
        for s in socials[:3]:
            print(f"    → {GRAY}{s[:60]}{RESET}")

    print(f"\n  {BOLD}--- ICP Scoring ---{RESET}")
    print(f"  ICP Score:    {color_score(icp)}/100")
    print(f"  Risk Level:   {color_risk(risk)}")

    if reasoning:
        print(f"\n  {BOLD}Score Breakdown:{RESET}")
        for key, val in reasoning.items():
            flag = val.get("flag", "")
            pts = val.get("points", 0)
            flag_color = YELLOW if pts > 0 else GREEN
            print(f"    {key:<20} {flag_color}{flag:<25}{RESET} +{pts}pts" if pts else
                  f"    {key:<20} {flag_color}{flag:<25}{RESET}")

    if llm:
        print(f"\n  {BOLD}LLM Reasoning:{RESET}")
        print(f"  {GRAY}{llm[:400]}{RESET}")

    if llm_analysis and isinstance(llm_analysis, dict):
        if llm_analysis.get("opportunity_summary"):
            print(f"\n  {BOLD}Opportunity:{RESET}")
            print(f"  {llm_analysis['opportunity_summary'][:300]}")
        if llm_analysis.get("top_pain_points"):
            print(f"\n  {BOLD}Pain Points:{RESET}")
            for p in llm_analysis["top_pain_points"][:3]:
                print(f"    • {p}")
        if llm_analysis.get("outreach_angle"):
            print(f"\n  {BOLD}Outreach Angle:{RESET}")
            print(f"  {BLUE}{llm_analysis['outreach_angle']}{RESET}")

    print(f"\n{'='*70}")


def _infer_status(analysis: dict) -> str:
    status = analysis.get("status", "unknown")
    if status == "success":
        return "reachable"
    if status == "error":
        return f"error_{analysis.get('code', '?')}"
    if status == "exception":
        err = analysis.get("error", "")
        if "NameResolution" in err:
            return "dns_failed"
        return "exception"
    return status


def prompt_action(lead: dict) -> dict:
    """Prompt user for review action and return review dict."""
    print(f"\n{BOLD}Actions:{RESET}")
    print(f"  [A] Approve  — accept score as-is")
    print(f"  [M] Modify   — override score")
    print(f"  [R] Reject   — remove from pipeline")
    print(f"  [S] Skip     — review later")
    print(f"  [Q] Quit     — save progress and exit")

    while True:
        choice = input(f"\n{BOLD}Your choice (A/M/R/S/Q): {RESET}").strip().upper()

        if choice == "Q":
            return {"action": "quit"}

        if choice == "A":
            notes = input("  Notes (optional): ").strip()
            return {
                "action": "approve",
                "override_score": None,
                "notes": notes or None,
                "human_verified": True,
            }

        if choice == "M":
            while True:
                try:
                    raw = input("  New score (0-100): ").strip()
                    new_score = int(raw)
                    if 0 <= new_score <= 100:
                        break
                    print("  Score must be 0-100.")
                except ValueError:
                    print("  Enter a number.")
            notes = input("  Reason for override: ").strip()
            return {
                "action": "modify",
                "override_score": new_score,
                "notes": notes or None,
                "human_verified": True,
            }

        if choice == "R":
            notes = input("  Reason for rejection: ").strip()
            return {
                "action": "reject",
                "override_score": 0,
                "notes": notes or "Rejected by reviewer",
                "human_verified": True,
            }

        if choice == "S":
            return {"action": "skip", "human_verified": False}

        print("  Invalid choice. Enter A, M, R, S, or Q.")


def run_review(leads: list[dict], db_path: str = None, start_from: int = 0):
    """Main review loop."""
    db = db_path or str(ROOT / "data" / "leads.db")
    conn = get_conn(db)
    init_db(db)

    reviewable = [l for l in leads if l.get("score")]
    if not reviewable:
        print(f"{YELLOW}No scored leads to review. Run the scoring pipeline first.{RESET}")
        return

    total = len(reviewable)
    print(f"\n{BOLD}{CYAN}=== ICP Lead Review System ==={RESET}")
    print(f"Reviewing {total} scored leads. Decisions saved to: {db}")
    print(f"Press Ctrl+C at any time — progress is saved after each lead.\n")

    approved = modified = rejected = skipped = 0

    for i, lead in enumerate(reviewable[start_from:], start=start_from + 1):
        render_lead(lead, i, total)
        review = prompt_action(lead)

        if review.get("action") == "quit":
            print(f"\n{YELLOW}Exiting. Progress saved.{RESET}")
            break

        if review.get("action") == "skip":
            skipped += 1
            continue

        # Persist to SQLite
        lead_id = upsert_lead(conn, {
            "business_name": lead.get("business_name"),
            "website": lead.get("website") or lead.get("url"),
            "category": lead.get("category"),
            "geo_area": lead.get("geo_area", "ZIP 30350"),
            "address": lead.get("address"),
            "phone": lead.get("phone"),
            "email": lead.get("email"),
        })

        enrichment = lead.get("enrichment") or {}
        if enrichment:
            upsert_enrichment(conn, lead_id, enrichment)

        score = lead.get("score", {})
        upsert_score(conn, lead_id, {
            "icp_score": score.get("icp_score"),
            "risk_level": score.get("risk_level"),
            "reasoning": score.get("reasoning"),
            "ollama_summary": score.get("ollama_summary"),
            "model_used": score.get("model_used"),
        })

        upsert_human_review(conn, lead_id, review)

        action = review["action"]
        if action == "approve":
            approved += 1
            print(f"  {GREEN}✓ Approved{RESET}")
        elif action == "modify":
            modified += 1
            print(f"  {YELLOW}✓ Score modified → {review['override_score']}{RESET}")
        elif action == "reject":
            rejected += 1
            print(f"  {RED}✗ Rejected{RESET}")

    # Export CSV
    csv_path = str(ROOT / "data" / "scored_leads.csv")
    export_csv(conn, csv_path)
    conn.close()

    print(f"\n{'='*70}")
    print(f"{BOLD}Review Complete{RESET}")
    print(f"  Approved: {GREEN}{approved}{RESET}")
    print(f"  Modified: {YELLOW}{modified}{RESET}")
    print(f"  Rejected: {RED}{rejected}{RESET}")
    print(f"  Skipped:  {skipped}")
    print(f"\nFinal CSV exported → {csv_path}")


def main():
    parser = argparse.ArgumentParser(description="Human-in-the-loop ICP lead review")
    parser.add_argument("--input", default=None, help="Scored leads JSON file")
    parser.add_argument("--db", default=None, help="SQLite database path")
    parser.add_argument("--pending", action="store_true", help="Only show pending (un-reviewed) leads from DB")
    parser.add_argument("--from", dest="start_from", type=int, default=0, help="Resume from lead index")
    args = parser.parse_args()

    if args.pending:
        db = args.db or str(ROOT / "data" / "leads.db")
        conn = get_conn(db)
        leads = get_pending_review(conn)
        conn.close()
        if not leads:
            print("No pending leads in database.")
            return
        # Wrap DB rows into expected format
        leads = [{"business_name": l["business_name"], "website": l["website"],
                   "category": l["category"], "address": l.get("address", ""),
                   "score": {"icp_score": l["icp_score"], "risk_level": l["risk_level"],
                              "reasoning": json.loads(l["reasoning"] or "{}"),
                              "ollama_summary": l["ollama_summary"]}} for l in leads]
    else:
        in_path = args.input or str(ROOT / "data" / "scored_leads_full.json")
        if not Path(in_path).exists():
            # Fallback chain
            for alt in ["data/enriched_leads.json", "data/analyzed_leads.json"]:
                alt_path = ROOT / alt
                if alt_path.exists():
                    in_path = str(alt_path)
                    break

        if not Path(in_path).exists():
            print(f"No input file found. Run the scoring pipeline first.")
            return

        with open(in_path) as f:
            leads = json.load(f)

    run_review(leads, db_path=args.db, start_from=args.start_from)


if __name__ == "__main__":
    main()

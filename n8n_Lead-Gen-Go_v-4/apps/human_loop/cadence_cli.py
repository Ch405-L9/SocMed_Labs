#!/usr/bin/env python3
"""
Outreach cadence tracker CLI.
Log contact attempts, track responses, and surface follow-up reminders.

Commands:
  list        Show all leads with outreach status and scores
  log         Record a new contact attempt for a lead
  followups   Show leads with overdue follow-ups (default: today)
  history     Show full contact history for a specific lead
  export      Export cadence log to CSV
"""

import sys
import argparse
import json
from pathlib import Path
from datetime import date, datetime

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "storage"))

try:
    import db
except ImportError as e:
    print(f"Error importing db module: {e}")
    sys.exit(1)

RESPONSE_CHOICES = ["no_response", "interested", "not_interested", "scheduled", "bounced"]
CHANNEL_CHOICES = ["email", "phone", "walk_in", "linkedin", "other"]

COLORS = {
    "reset":  "\033[0m",
    "bold":   "\033[1m",
    "red":    "\033[91m",
    "yellow": "\033[93m",
    "green":  "\033[92m",
    "cyan":   "\033[96m",
    "gray":   "\033[90m",
}


def c(text, *codes):
    return "".join(COLORS.get(k, "") for k in codes) + str(text) + COLORS["reset"]


def fmt_date(val):
    if not val:
        return c("—", "gray")
    try:
        d = datetime.fromisoformat(str(val).replace("Z", ""))
        return d.strftime("%Y-%m-%d")
    except Exception:
        return str(val)


def fmt_response(r):
    mapping = {
        "no_response":      c("no response",     "gray"),
        "interested":       c("interested",       "green"),
        "not_interested":   c("not interested",   "red"),
        "scheduled":        c("scheduled",        "cyan"),
        "bounced":          c("bounced",          "yellow"),
    }
    return mapping.get(r, r or c("—", "gray"))


def score_color(score):
    if score is None:
        return c("?", "gray")
    if score >= 70:
        return c(score, "red", "bold")
    if score >= 40:
        return c(score, "yellow")
    return c(score, "green")


def cmd_list(conn, args):
    rows = db.get_outreach_summary(conn)
    if not rows:
        # Fall back to showing all leads even without scores
        all_leads = conn.execute(
            """SELECT l.id, l.business_name, l.website, l.category,
                      e.primary_phone, e.primary_email,
                      s.icp_score AS final_score, s.risk_level,
                      0 AS contact_attempts, NULL AS last_contacted,
                      NULL AS next_follow_up, NULL AS last_response,
                      0 AS human_verified
               FROM leads l
               LEFT JOIN enrichment e ON e.lead_id = l.id
               LEFT JOIN scores s     ON s.lead_id = l.id
               ORDER BY s.icp_score DESC NULLS LAST"""
        ).fetchall()
        rows = [dict(r) for r in all_leads]

    if not rows:
        print("No leads found. Run the pipeline first to populate the database.")
        return

    print()
    print(c(f"{'ID':>4}  {'Business Name':<35} {'Score':>5}  {'Attempts':>8}  {'Last Contact':<13}  {'Follow-Up':<11}  {'Last Response'}", "bold"))
    print("─" * 110)

    for r in rows:
        score = r.get("final_score")
        attempts = r.get("contact_attempts", 0)
        follow_up = r.get("next_follow_up")
        overdue = False
        if follow_up and follow_up <= date.today().isoformat():
            overdue = True

        fu_str = c(follow_up, "red", "bold") if overdue else fmt_date(follow_up)
        name = (r.get("business_name") or "?")[:34]

        print(
            f"{r['id']:>4}  {name:<35} {score_color(score):>5}  "
            f"{attempts:>8}  {fmt_date(r.get('last_contacted')):<13}  "
            f"{fu_str:<11}  {fmt_response(r.get('last_response'))}"
        )

    print()
    overdue_count = sum(
        1 for r in rows
        if r.get("next_follow_up") and r["next_follow_up"] <= date.today().isoformat()
    )
    if overdue_count:
        print(c(f"  {overdue_count} lead(s) have overdue follow-ups. Run: cadence_cli.py followups", "red"))
    print()


def cmd_log(conn, args):
    lead_id = args.lead_id

    # Verify lead exists
    row = conn.execute("SELECT id, business_name FROM leads WHERE id=?", (lead_id,)).fetchone()
    if not row:
        print(c(f"No lead found with ID {lead_id}.", "red"))
        return

    name = row["business_name"]

    # Prompt for missing fields interactively
    channel = args.channel
    if not channel:
        print(f"Logging contact for: {c(name, 'bold', 'cyan')}")
        print(f"Channel options: {', '.join(CHANNEL_CHOICES)}")
        channel = input("Channel: ").strip().lower() or "other"

    notes = args.notes
    if notes is None:
        notes = input("Notes (optional): ").strip() or None

    response = args.response
    if not response:
        print(f"Response options: {', '.join(RESPONSE_CHOICES)}")
        response = input("Response [no_response]: ").strip().lower() or "no_response"

    contact_person = args.contact_person
    if contact_person is None:
        contact_person = input("Contact person name/role (optional): ").strip() or None

    follow_up_date = args.follow_up
    if follow_up_date is None:
        fu = input("Follow-up date YYYY-MM-DD (leave blank to skip): ").strip()
        follow_up_date = fu if fu else None

    entry = {
        "channel": channel,
        "notes": notes,
        "response": response,
        "contact_person": contact_person,
        "follow_up_date": follow_up_date,
    }

    log_id = db.log_outreach(conn, lead_id, entry)
    print(c(f"\nLogged outreach #{log_id} for '{name}' via {channel}.", "green"))
    if follow_up_date:
        print(c(f"Follow-up scheduled: {follow_up_date}", "cyan"))


def cmd_followups(conn, args):
    as_of = args.date or date.today().isoformat()
    rows = db.get_pending_followups(conn, as_of=as_of)

    if not rows:
        print(c(f"\nNo pending follow-ups as of {as_of}.", "green"))
        return

    print()
    print(c(f"Pending follow-ups as of {as_of} ({len(rows)} total):", "bold", "yellow"))
    print("─" * 90)

    for r in rows:
        name = (r.get("business_name") or "?")[:40]
        channel = r.get("channel", "other")
        fu_date = r.get("follow_up_date", "")
        phone = r.get("primary_phone") or "—"
        email = r.get("primary_email") or "—"

        print(f"\n  {c(name, 'bold')}  (Lead ID: {r['lead_id']})")
        print(f"    Follow-up date : {c(fu_date, 'red', 'bold')}")
        print(f"    Channel        : {channel}")
        print(f"    Phone          : {phone}")
        print(f"    Email          : {email}")
        if r.get("notes"):
            print(f"    Notes          : {r['notes']}")

    print()
    print(c("To update a response, run:", "gray"))
    print(c("  python cadence_cli.py update <log_id> --response interested", "gray"))
    print()


def cmd_history(conn, args):
    lead_id = args.lead_id
    row = conn.execute("SELECT id, business_name, website FROM leads WHERE id=?", (lead_id,)).fetchone()
    if not row:
        print(c(f"No lead found with ID {lead_id}.", "red"))
        return

    name = row["business_name"]
    website = row["website"] or "—"
    print()
    print(c(f"Outreach history — {name}", "bold", "cyan"))
    print(c(f"Website: {website}", "gray"))
    print("─" * 80)

    entries = db.get_outreach_history(conn, lead_id)
    if not entries:
        print(c("  No contact attempts recorded yet.", "gray"))
    else:
        for e in entries:
            print(f"\n  [{fmt_date(e.get('contacted_at'))}]  "
                  f"{c(e.get('channel','other'), 'bold')}  →  {fmt_response(e.get('response'))}")
            if e.get("contact_person"):
                print(f"    Person     : {e['contact_person']}")
            if e.get("notes"):
                print(f"    Notes      : {e['notes']}")
            if e.get("follow_up_date"):
                print(f"    Follow-up  : {e['follow_up_date']}")
            print(f"    Log ID     : {e['id']}")
    print()


def cmd_update(conn, args):
    log_id = args.log_id
    response = args.response
    notes = args.notes

    row = conn.execute("SELECT id FROM outreach_log WHERE id=?", (log_id,)).fetchone()
    if not row:
        print(c(f"No outreach log entry with ID {log_id}.", "red"))
        return

    db.update_outreach_response(conn, log_id, response, notes)
    print(c(f"Updated log #{log_id}: response = {response}", "green"))


def cmd_export(conn, args):
    out_path = args.out or str(ROOT / "data" / "outreach_cadence.csv")
    db.export_cadence_csv(conn, out_path)
    print(c(f"Cadence log exported → {out_path}", "green"))


def main():
    parser = argparse.ArgumentParser(
        description="Outreach Cadence Tracker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cadence_cli.py list
  python cadence_cli.py log 5 --channel email --response interested --follow-up 2026-04-30
  python cadence_cli.py followups
  python cadence_cli.py followups --date 2026-04-20
  python cadence_cli.py history 5
  python cadence_cli.py update 12 --response scheduled --notes "Call booked for Friday"
  python cadence_cli.py export --out data/outreach_cadence.csv
        """,
    )
    parser.add_argument("--db", default=None, help="Path to SQLite database (default: data/leads.db)")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # list
    subparsers.add_parser("list", help="Show all leads with outreach status")

    # log
    p_log = subparsers.add_parser("log", help="Record a contact attempt")
    p_log.add_argument("lead_id", type=int, help="Lead ID (from 'list' command)")
    p_log.add_argument("--channel", choices=CHANNEL_CHOICES, help="Contact channel")
    p_log.add_argument("--response", choices=RESPONSE_CHOICES, help="Lead response")
    p_log.add_argument("--notes", help="Additional notes")
    p_log.add_argument("--contact-person", dest="contact_person", help="Name or role of person contacted")
    p_log.add_argument("--follow-up", dest="follow_up", metavar="YYYY-MM-DD", help="Schedule follow-up date")

    # followups
    p_fu = subparsers.add_parser("followups", help="Show overdue follow-ups")
    p_fu.add_argument("--date", metavar="YYYY-MM-DD", help="Check as of date (default: today)")

    # history
    p_hist = subparsers.add_parser("history", help="Show contact history for a lead")
    p_hist.add_argument("lead_id", type=int, help="Lead ID")

    # update
    p_upd = subparsers.add_parser("update", help="Update response on an existing log entry")
    p_upd.add_argument("log_id", type=int, help="Outreach log entry ID")
    p_upd.add_argument("--response", choices=RESPONSE_CHOICES, required=True)
    p_upd.add_argument("--notes", help="Optional notes to append")

    # export
    p_exp = subparsers.add_parser("export", help="Export cadence log to CSV")
    p_exp.add_argument("--out", help="Output CSV path (default: data/outreach_cadence.csv)")

    args = parser.parse_args()

    db_path = args.db or str(ROOT / "data" / "leads.db")
    if not Path(db_path).exists():
        print(c(f"Database not found: {db_path}", "red"))
        print("Run the pipeline first: python scripts/run_pipeline.py")
        sys.exit(1)

    conn = db.get_conn(db_path)
    db.migrate_db(conn)

    try:
        if args.command == "list":
            cmd_list(conn, args)
        elif args.command == "log":
            cmd_log(conn, args)
        elif args.command == "followups":
            cmd_followups(conn, args)
        elif args.command == "history":
            cmd_history(conn, args)
        elif args.command == "update":
            cmd_update(conn, args)
        elif args.command == "export":
            cmd_export(conn, args)
    finally:
        conn.close()


if __name__ == "__main__":
    main()

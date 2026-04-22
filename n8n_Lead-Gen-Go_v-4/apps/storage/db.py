import sqlite3
import json
import csv
import os
from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = Path(__file__).parent / "schema.sql"
DB_PATH = ROOT / "data" / "leads.db"

# New columns added in v1.1.0 — applied via migrate_db() on existing databases
_ENRICHMENT_V11_COLUMNS = [
    ("phone_numbers",           "TEXT"),
    ("primary_phone",           "TEXT"),
    ("email_addresses",         "TEXT"),
    ("primary_email",           "TEXT"),
    ("mx_verified",             "INTEGER DEFAULT 0"),
    ("pagespeed_performance",   "INTEGER"),
    ("pagespeed_seo",           "INTEGER"),
    ("pagespeed_accessibility", "INTEGER"),
]

# New columns added in v1.2.0
_ENRICHMENT_V12_COLUMNS = [
    ("last_crawled",    "TEXT"),
    ("content_hash",    "TEXT"),
    ("gbp_rating",      "REAL"),
    ("gbp_review_count","INTEGER"),
    ("gbp_photo_count", "INTEGER"),
    ("gbp_verified",    "INTEGER DEFAULT 0"),
    ("gbp_unclaimed",   "INTEGER DEFAULT 0"),
]

_SCORES_V12_COLUMNS = [
    ("prompt_version", "TEXT"),
]


def get_conn(db_path: str = None) -> sqlite3.Connection:
    path = db_path or str(DB_PATH)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(db_path: str = None):
    conn = get_conn(db_path)
    with open(SCHEMA) as f:
        conn.executescript(f.read())
    conn.commit()
    migrate_db(conn)
    conn.close()


def migrate_db(conn: sqlite3.Connection):
    """
    Non-destructive schema migration for databases created before v1.1.0.
    Adds new columns to enrichment table and recreates the leads_full view.
    """
    for col, col_type in _ENRICHMENT_V11_COLUMNS + _ENRICHMENT_V12_COLUMNS:
        try:
            conn.execute(f"ALTER TABLE enrichment ADD COLUMN {col} {col_type}")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # Column already exists — safe to skip

    for col, col_type in _SCORES_V12_COLUMNS:
        try:
            conn.execute(f"ALTER TABLE scores ADD COLUMN {col} {col_type}")
            conn.commit()
        except sqlite3.OperationalError:
            pass

    # Recreate views to include new columns (DROP IF EXISTS + re-run schema)
    try:
        conn.execute("DROP VIEW IF EXISTS leads_full")
        conn.execute("DROP VIEW IF EXISTS outreach_summary")
        conn.commit()
        with open(SCHEMA) as f:
            conn.executescript(f.read())
        conn.commit()
    except Exception:
        pass


def upsert_lead(conn: sqlite3.Connection, lead: dict) -> int:
    cur = conn.execute(
        "SELECT id FROM leads WHERE business_name=? AND address=?",
        (lead.get("business_name"), lead.get("address", "")),
    )
    row = cur.fetchone()
    if row:
        conn.execute(
            "UPDATE leads SET website=?, phone=?, email=? WHERE id=?",
            (lead.get("website"), lead.get("phone"), lead.get("email"), row["id"]),
        )
        conn.commit()
        return row["id"]
    cur = conn.execute(
        """INSERT INTO leads (business_name, website, category, geo_area, address, phone, email)
           VALUES (?,?,?,?,?,?,?)""",
        (
            lead.get("business_name"),
            lead.get("website"),
            lead.get("category"),
            lead.get("geo_area"),
            lead.get("address"),
            lead.get("phone"),
            lead.get("email"),
        ),
    )
    conn.commit()
    return cur.lastrowid


def upsert_enrichment(conn: sqlite3.Connection, lead_id: int, enrichment: dict):
    conn.execute("DELETE FROM enrichment WHERE lead_id=?", (lead_id,))
    conn.execute(
        """INSERT INTO enrichment
           (lead_id, website_status, http_code, is_https, booking_present,
            contact_form, seo_title, seo_description, has_seo,
            social_links, social_count, page_summary,
            phone_numbers, primary_phone, email_addresses, primary_email, mx_verified,
            pagespeed_performance, pagespeed_seo, pagespeed_accessibility,
            last_crawled, content_hash,
            gbp_rating, gbp_review_count, gbp_photo_count, gbp_verified, gbp_unclaimed)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            lead_id,
            enrichment.get("website_status"),
            enrichment.get("http_code"),
            int(bool(enrichment.get("is_https", False))),
            int(bool(enrichment.get("booking_present", False))),
            int(bool(enrichment.get("contact_form", False))),
            enrichment.get("seo_title"),
            enrichment.get("seo_description"),
            int(bool(enrichment.get("has_seo", False))),
            json.dumps(enrichment.get("social_links", [])),
            enrichment.get("social_count", 0),
            enrichment.get("page_summary"),
            json.dumps(enrichment.get("phone_numbers", [])),
            enrichment.get("primary_phone"),
            json.dumps(enrichment.get("email_addresses", [])),
            enrichment.get("primary_email"),
            int(bool(enrichment.get("mx_verified", False))),
            enrichment.get("pagespeed_performance"),
            enrichment.get("pagespeed_seo"),
            enrichment.get("pagespeed_accessibility"),
            enrichment.get("last_crawled"),
            enrichment.get("content_hash"),
            enrichment.get("gbp_rating"),
            enrichment.get("gbp_review_count"),
            enrichment.get("gbp_photo_count"),
            int(bool(enrichment.get("gbp_verified", False))),
            int(bool(enrichment.get("gbp_unclaimed", False))),
        ),
    )
    conn.commit()


def upsert_score(conn: sqlite3.Connection, lead_id: int, score: dict):
    conn.execute("DELETE FROM scores WHERE lead_id=?", (lead_id,))
    conn.execute(
        """INSERT INTO scores
           (lead_id, icp_score, risk_level, reasoning, ollama_summary, model_used, prompt_version)
           VALUES (?,?,?,?,?,?,?)""",
        (
            lead_id,
            score.get("icp_score"),
            score.get("risk_level"),
            json.dumps(score.get("reasoning", {})),
            score.get("ollama_summary"),
            score.get("model_used"),
            score.get("prompt_version"),
        ),
    )
    conn.commit()


def get_human_overrides(conn: sqlite3.Connection) -> list[dict]:
    """
    Return leads where a human explicitly overrode the model score.
    Each row includes the model icp_score, the human override_score, and reasoning JSON.
    Only includes rows where override_score IS NOT NULL and differs from icp_score.
    """
    rows = conn.execute(
        """SELECT s.icp_score, s.reasoning, r.override_score, r.action, r.notes,
                  l.business_name, l.category
           FROM human_reviews r
           JOIN scores s ON s.lead_id = r.lead_id
           JOIN leads l  ON l.id = r.lead_id
           WHERE r.override_score IS NOT NULL
             AND r.override_score != s.icp_score"""
    ).fetchall()
    return [dict(row) for row in rows]


def get_enrichment_cache(conn: sqlite3.Connection) -> dict:
    """
    Return a dict of website_url -> {last_crawled, content_hash} for incremental crawl.
    Only includes rows where last_crawled is not null.
    """
    rows = conn.execute(
        """SELECT l.website, e.last_crawled, e.content_hash
           FROM enrichment e
           JOIN leads l ON l.id = e.lead_id
           WHERE e.last_crawled IS NOT NULL"""
    ).fetchall()
    return {
        row["website"]: {"last_crawled": row["last_crawled"], "content_hash": row["content_hash"]}
        for row in rows
        if row["website"]
    }


def upsert_human_review(conn: sqlite3.Connection, lead_id: int, review: dict):
    conn.execute("DELETE FROM human_reviews WHERE lead_id=?", (lead_id,))
    conn.execute(
        """INSERT INTO human_reviews
           (lead_id, action, override_score, notes, human_verified)
           VALUES (?,?,?,?,?)""",
        (
            lead_id,
            review.get("action"),
            review.get("override_score"),
            review.get("notes"),
            int(bool(review.get("human_verified", False))),
        ),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Outreach Cadence
# ---------------------------------------------------------------------------

def log_outreach(conn: sqlite3.Connection, lead_id: int, entry: dict) -> int:
    """Insert a new outreach log entry. Returns the new row id."""
    cur = conn.execute(
        """INSERT INTO outreach_log
           (lead_id, channel, contacted_at, contact_person, notes, response, follow_up_date)
           VALUES (?,?,CURRENT_TIMESTAMP,?,?,?,?)""",
        (
            lead_id,
            entry.get("channel", "other"),
            entry.get("contact_person"),
            entry.get("notes"),
            entry.get("response", "no_response"),
            entry.get("follow_up_date"),
        ),
    )
    conn.commit()
    return cur.lastrowid


def update_outreach_response(conn: sqlite3.Connection, log_id: int, response: str, notes: str = None):
    """Update the response field on an existing outreach log entry."""
    conn.execute(
        "UPDATE outreach_log SET response=?, notes=COALESCE(?,notes) WHERE id=?",
        (response, notes, log_id),
    )
    conn.commit()


def get_outreach_history(conn: sqlite3.Connection, lead_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM outreach_log WHERE lead_id=? ORDER BY contacted_at DESC",
        (lead_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_pending_followups(conn: sqlite3.Connection, as_of: str = None) -> list[dict]:
    """
    Return outreach log entries where follow_up_date <= as_of (default today)
    and response is still 'no_response'.
    """
    cutoff = as_of or date.today().isoformat()
    rows = conn.execute(
        """SELECT o.*, l.business_name, l.website, l.category, l.address,
                  e.primary_phone, e.primary_email
           FROM outreach_log o
           JOIN leads l ON l.id = o.lead_id
           LEFT JOIN enrichment e ON e.lead_id = o.lead_id
           WHERE o.follow_up_date <= ?
             AND o.response = 'no_response'
           ORDER BY o.follow_up_date ASC""",
        (cutoff,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_outreach_summary(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT * FROM outreach_summary ORDER BY final_score DESC").fetchall()
    return [dict(r) for r in rows]


def export_csv(conn: sqlite3.Connection, out_path: str):
    rows = conn.execute("SELECT * FROM leads_full").fetchall()
    if not rows:
        return
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows([dict(r) for r in rows])


def export_cadence_csv(conn: sqlite3.Connection, out_path: str):
    """Export the outreach_summary view plus full log to a cadence CSV."""
    rows = conn.execute(
        """SELECT o.id, l.business_name, l.category, l.address,
                  e.primary_phone, e.primary_email,
                  COALESCE(r.override_score, s.icp_score) AS final_score,
                  s.risk_level,
                  o.channel, o.contacted_at, o.contact_person,
                  o.response, o.follow_up_date, o.notes
           FROM outreach_log o
           JOIN leads l ON l.id = o.lead_id
           LEFT JOIN enrichment e    ON e.lead_id = o.lead_id
           LEFT JOIN scores s        ON s.lead_id = o.lead_id
           LEFT JOIN human_reviews r ON r.lead_id = o.lead_id
           ORDER BY o.contacted_at DESC"""
    ).fetchall()
    if not rows:
        return
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows([dict(r) for r in rows])


def get_all_leads_full(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT * FROM leads_full").fetchall()
    return [dict(r) for r in rows]


def get_pending_review(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """SELECT l.id, l.business_name, l.website, l.category, l.address,
                  e.website_status, e.booking_present, e.has_seo, e.social_count,
                  e.primary_phone, e.primary_email, e.pagespeed_performance,
                  s.icp_score, s.risk_level, s.reasoning, s.ollama_summary
           FROM leads l
           LEFT JOIN enrichment e ON e.lead_id = l.id
           LEFT JOIN scores s ON s.lead_id = l.id
           LEFT JOIN human_reviews r ON r.lead_id = l.id
           WHERE r.id IS NULL AND s.id IS NOT NULL
           ORDER BY s.icp_score DESC"""
    ).fetchall()
    return [dict(r) for r in rows]

#!/usr/bin/env python3
"""
Read-only web dashboard for ICP lead data.
Serves lead table, lead detail, charts, and CSV download on localhost.

Usage:
  python scripts/serve_dashboard.py
  python scripts/serve_dashboard.py --port 8080
  python scripts/serve_dashboard.py --db data/leads.db --port 9000

Requires: pip install fastapi uvicorn jinja2
"""

import sys
import json
import argparse
import logging
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "apps" / "storage"))

log = logging.getLogger("dashboard")

try:
    from fastapi import FastAPI, Request, HTTPException
    from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
    from fastapi.templating import Jinja2Templates
    import uvicorn
except ImportError:
    print("Dashboard requires FastAPI and Uvicorn.")
    print("Install with: pip install fastapi uvicorn")
    sys.exit(1)

import db as dbmod

app = FastAPI(title="ICP Lead Dashboard", docs_url=None, redoc_url=None)
templates = Jinja2Templates(directory=str(ROOT / "templates"))

_DB_PATH = str(ROOT / "data" / "leads.db")


def get_conn():
    return dbmod.get_conn(_DB_PATH)


def _parse_reasoning(raw) -> dict:
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except Exception:
        return {}


def _enrich_lead(lead: dict) -> dict:
    """Parse JSON fields and add computed fields."""
    lead["reasoning_parsed"] = _parse_reasoning(lead.get("reasoning"))
    lead["final_score"] = lead.get("final_score") or lead.get("icp_score")
    for bool_field in ("booking_present", "has_seo", "is_https", "mx_verified",
                       "gbp_verified", "gbp_unclaimed", "human_verified"):
        if lead.get(bool_field) is not None:
            lead[bool_field] = bool(lead[bool_field])
    return lead


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    conn = get_conn()
    try:
        rows = conn.execute("SELECT * FROM leads_full ORDER BY final_score DESC NULLS LAST").fetchall()
        leads = [_enrich_lead(dict(r)) for r in rows]
    finally:
        conn.close()
    return templates.TemplateResponse("index.html", {"request": request, "leads": leads})


@app.get("/lead/{lead_id}", response_class=HTMLResponse)
async def lead_detail(request: Request, lead_id: int):
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM leads_full WHERE id=?", (lead_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Lead not found")
        lead = _enrich_lead(dict(row))
        outreach = dbmod.get_outreach_history(conn, lead_id)
    finally:
        conn.close()

    reasoning = lead.get("reasoning_parsed", {})
    return templates.TemplateResponse("lead_detail.html", {
        "request": request,
        "lead": lead,
        "reasoning": reasoning,
        "outreach": outreach,
    })


@app.get("/charts", response_class=HTMLResponse)
async def charts_page(request: Request):
    viz_dir = ROOT / "viz" / "output"
    chart_labels = {
        "score_distribution": "Score Distribution",
        "category_breakdown": "Category Breakdown",
        "high_priority_leads": "High Priority Leads",
        "correlation_matrix": "Digital Presence Correlation",
        "review_summary": "Human Review Summary",
    }
    chart_list = []
    if viz_dir.exists():
        for png in sorted(viz_dir.glob("*.png")):
            stem = png.stem
            label = chart_labels.get(stem, stem.replace("_", " ").title())
            chart_list.append({"filename": png.name, "label": label})

    return templates.TemplateResponse("charts.html", {
        "request": request,
        "charts": chart_list,
    })


@app.get("/chart/{filename}")
async def serve_chart(filename: str):
    path = ROOT / "viz" / "output" / filename
    if not path.exists() or not filename.endswith(".png"):
        raise HTTPException(status_code=404)
    return FileResponse(str(path), media_type="image/png")


@app.get("/export")
async def export_csv():
    csv_path = ROOT / "data" / "scored_leads.csv"
    if not csv_path.exists():
        raise HTTPException(status_code=404, detail="scored_leads.csv not found. Run the export step first.")
    return FileResponse(
        str(csv_path),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=scored_leads.csv"},
    )


@app.get("/api/leads")
async def api_leads():
    """JSON API endpoint for leads data."""
    conn = get_conn()
    try:
        rows = conn.execute("SELECT * FROM leads_full ORDER BY final_score DESC NULLS LAST").fetchall()
        return [_enrich_lead(dict(r)) for r in rows]
    finally:
        conn.close()


@app.get("/api/lead/{lead_id}")
async def api_lead(lead_id: int):
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM leads_full WHERE id=?", (lead_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404)
        lead = _enrich_lead(dict(row))
        lead["outreach_history"] = dbmod.get_outreach_history(conn, lead_id)
        return lead
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="ICP Lead Dashboard")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8080, help="Port (default: 8080)")
    parser.add_argument("--db", default=None, help="Path to SQLite database")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    args = parser.parse_args()

    global _DB_PATH
    if args.db:
        _DB_PATH = args.db

    if not Path(_DB_PATH).exists():
        print(f"Database not found: {_DB_PATH}")
        print("Run the pipeline first: python scripts/run_pipeline.py")
        sys.exit(1)

    print(f"\nICP Lead Dashboard")
    print(f"  Database : {_DB_PATH}")
    print(f"  URL      : http://{args.host}:{args.port}")
    print(f"  Press Ctrl+C to stop\n")

    uvicorn.run(
        "serve_dashboard:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="warning",
        app_dir=str(Path(__file__).parent),
    )


if __name__ == "__main__":
    main()

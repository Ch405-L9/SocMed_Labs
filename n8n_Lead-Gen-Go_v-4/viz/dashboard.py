#!/usr/bin/env python3
"""
ICP Lead Generation Visualization Dashboard.
Generates charts from scored leads data.
"""

import json
import csv
import argparse
import logging
import os
from pathlib import Path

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "viz" / "output"


def load_data(scored_csv: str = None, scored_json: str = None) -> pd.DataFrame:
    """Load scored leads from CSV or JSON into a DataFrame."""
    # Try CSV first
    csv_path = scored_csv or str(ROOT / "data" / "scored_leads.csv")
    if Path(csv_path).exists():
        df = pd.read_csv(csv_path)
        log.info("Loaded %d rows from %s", len(df), csv_path)
        return df

    # Fall back to JSON
    json_paths = [
        scored_json,
        str(ROOT / "data" / "scored_leads_full.json"),
        str(ROOT / "data" / "enriched_leads.json"),
        str(ROOT / "data" / "analyzed_leads.json"),
    ]
    for jpath in json_paths:
        if jpath and Path(jpath).exists():
            with open(jpath) as f:
                raw = json.load(f)
            rows = []
            for lead in raw:
                score = lead.get("score", {})
                enrichment = lead.get("enrichment") or lead.get("analysis") or {}
                rows.append({
                    "business_name": lead.get("business_name") or lead.get("name"),
                    "category": lead.get("category"),
                    "website": lead.get("website") or lead.get("url"),
                    "address": lead.get("address"),
                    "icp_score": score.get("icp_score"),
                    "final_score": score.get("icp_score"),
                    "risk_level": score.get("risk_level"),
                    "website_status": enrichment.get("website_status") or enrichment.get("status"),
                    "booking_present": enrichment.get("booking_present") or enrichment.get("booking", False),
                    "has_seo": enrichment.get("has_seo", False),
                    "social_count": enrichment.get("social_count") or len(enrichment.get("socials", [])),
                    "human_verified": lead.get("human_verified", False),
                    "human_action": lead.get("human_action"),
                })
            df = pd.DataFrame(rows)
            log.info("Loaded %d rows from %s", len(df), jpath)
            return df

    # Fall back to CSV in data/
    csv_legacy = ROOT / "data" / "healthcare_leads_30350.csv"
    if csv_legacy.exists():
        df = pd.read_csv(csv_legacy)
        log.info("Using legacy CSV: %s", csv_legacy)
        rename = {
            "Business Name": "business_name",
            "Category": "category",
            "Website URL": "website",
            "Full Address": "address",
            "ICP Score (0–100)": "icp_score",
            "Risk / Opportunity Level": "risk_level",
            "Digital Presence Quality": "digital_quality",
        }
        df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
        if "icp_score" in df.columns:
            df["final_score"] = pd.to_numeric(df["icp_score"], errors="coerce")
        return df

    raise FileNotFoundError("No scored leads data found. Run the pipeline first.")


def setup_style():
    try:
        plt.style.use("seaborn-v0_8-darkgrid")
    except Exception:
        plt.style.use("ggplot")
    sns.set_palette("husl")


def plot_score_distribution(df: pd.DataFrame, out_dir: Path):
    """ICP score histogram by risk level."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    score_col = "final_score" if "final_score" in df.columns else "icp_score"
    data = df[score_col].dropna()

    # Histogram
    ax = axes[0]
    colors = {"high": "#e74c3c", "medium": "#f39c12", "low": "#27ae60"}
    if "risk_level" in df.columns:
        for risk, grp in df.groupby("risk_level"):
            grp[score_col].dropna().plot.hist(
                bins=10, ax=ax, alpha=0.7,
                label=risk.title(), color=colors.get(risk, "steelblue")
            )
        ax.legend(title="Risk Level")
    else:
        data.plot.hist(bins=15, ax=ax, color="steelblue", alpha=0.8)

    ax.set_title("ICP Score Distribution", fontsize=13, fontweight="bold")
    ax.set_xlabel("ICP Score (0-100)")
    ax.set_ylabel("Count")
    ax.axvline(x=70, color="red", linestyle="--", alpha=0.5, label="High threshold")
    ax.axvline(x=40, color="orange", linestyle="--", alpha=0.5, label="Medium threshold")

    # Score bins bar chart as KDE alternative
    ax2 = axes[1]
    bins = {"0-39 (Low)": 0, "40-69 (Medium)": 0, "70-100 (High)": 0}
    for v in data:
        if v < 40:
            bins["0-39 (Low)"] += 1
        elif v < 70:
            bins["40-69 (Medium)"] += 1
        else:
            bins["70-100 (High)"] += 1
    bar_colors = ["#27ae60", "#f39c12", "#e74c3c"]
    ax2.bar(bins.keys(), bins.values(), color=bar_colors)
    ax2.set_title("Leads by Risk Band", fontsize=13, fontweight="bold")
    ax2.set_xlabel("ICP Score Band")
    ax2.set_ylabel("Count")

    plt.tight_layout()
    path = out_dir / "01_score_distribution.png"
    plt.savefig(path, dpi=150)
    plt.close()
    log.info("Saved: %s", path)


def plot_category_breakdown(df: pd.DataFrame, out_dir: Path):
    """ICP scores by business category."""
    if "category" not in df.columns:
        return

    score_col = "final_score" if "final_score" in df.columns else "icp_score"
    cat_data = df.groupby("category")[score_col].agg(["mean", "count"]).reset_index()
    cat_data = cat_data.sort_values("mean", ascending=False)

    fig, axes = plt.subplots(1, 2, figsize=(15, 5))

    # Mean score bar chart
    ax = axes[0]
    bars = ax.barh(cat_data["category"], cat_data["mean"], color=sns.color_palette("husl", len(cat_data)))
    ax.set_xlabel("Average ICP Score")
    ax.set_title("Avg ICP Score by Category", fontsize=13, fontweight="bold")
    ax.axvline(x=70, color="red", linestyle="--", alpha=0.5)
    ax.axvline(x=40, color="orange", linestyle="--", alpha=0.5)

    # Lead count
    ax2 = axes[1]
    ax2.barh(cat_data["category"], cat_data["count"], color=sns.color_palette("Set2", len(cat_data)))
    ax2.set_xlabel("Number of Leads")
    ax2.set_title("Lead Count by Category", fontsize=13, fontweight="bold")

    plt.tight_layout()
    path = out_dir / "02_category_breakdown.png"
    plt.savefig(path, dpi=150)
    plt.close()
    log.info("Saved: %s", path)


def plot_high_risk_leads(df: pd.DataFrame, out_dir: Path):
    """Horizontal bar chart of top high-priority leads."""
    score_col = "final_score" if "final_score" in df.columns else "icp_score"
    high = df[df[score_col].fillna(0) >= 60].copy()
    if high.empty:
        high = df.nlargest(15, score_col)

    high = high.sort_values(score_col, ascending=True).tail(20)
    names = high.get("business_name", high.index.astype(str))
    scores = high[score_col]

    colors = ["#e74c3c" if s >= 70 else "#f39c12" if s >= 40 else "#27ae60" for s in scores]

    fig, ax = plt.subplots(figsize=(12, max(5, len(high) * 0.4)))
    bars = ax.barh(names.values, scores.values, color=colors)

    ax.set_xlabel("ICP Score (0-100 — Higher = Better Fit)")
    ax.set_title("Top Opportunity Leads (High ICP Score)", fontsize=13, fontweight="bold")
    ax.axvline(x=70, color="darkred", linestyle="--", alpha=0.6, label="High risk threshold")
    ax.axvline(x=40, color="darkorange", linestyle="--", alpha=0.6, label="Medium risk threshold")
    ax.legend(loc="lower right")

    for bar, score in zip(bars, scores.values):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                f"{score:.0f}", va="center", fontsize=9)

    plt.tight_layout()
    path = out_dir / "03_high_priority_leads.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    log.info("Saved: %s", path)


def plot_digital_presence_correlation(df: pd.DataFrame, out_dir: Path):
    """Scatter: social count vs ICP score, colored by booking presence."""
    score_col = "final_score" if "final_score" in df.columns else "icp_score"

    numeric_cols = [score_col]
    signal_cols = []
    for col in ["social_count", "booking_present", "has_seo"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
            signal_cols.append(col)
            numeric_cols.append(col)

    if len(signal_cols) < 2:
        log.warning("Not enough signal columns for correlation plot.")
        return

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Social count vs score
    ax = axes[0]
    if "social_count" in df.columns:
        scatter_colors = df["booking_present"].map({1: "#27ae60", 0: "#e74c3c", True: "#27ae60", False: "#e74c3c"})
        ax.scatter(df["social_count"], df[score_col], c=scatter_colors, alpha=0.7, s=80)
        ax.set_xlabel("Social Media Platforms")
        ax.set_ylabel("ICP Score")
        ax.set_title("Social Presence vs ICP Score\n(green=has booking, red=no booking)", fontsize=11, fontweight="bold")

    # Correlation heatmap
    ax2 = axes[1]
    corr_df = df[numeric_cols].dropna()
    if len(corr_df) > 2:
        corr = corr_df.corr()
        sns.heatmap(corr, annot=True, fmt=".2f", ax=ax2, cmap="RdYlGn",
                    center=0, square=True, linewidths=0.5)
        ax2.set_title("Signal Correlation Matrix", fontsize=11, fontweight="bold")

    plt.tight_layout()
    path = out_dir / "04_digital_presence_correlation.png"
    plt.savefig(path, dpi=150)
    plt.close()
    log.info("Saved: %s", path)


def plot_review_summary(df: pd.DataFrame, out_dir: Path):
    """Human review decision breakdown."""
    if "human_action" not in df.columns and "human_verified" not in df.columns:
        return

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # Action breakdown
    ax = axes[0]
    if "human_action" in df.columns:
        action_counts = df["human_action"].value_counts()
        if not action_counts.empty:
            colors = {"approve": "#27ae60", "modify": "#f39c12", "reject": "#e74c3c", "skip": "#95a5a6"}
            ax.pie(action_counts.values, labels=action_counts.index,
                   colors=[colors.get(a, "steelblue") for a in action_counts.index],
                   autopct="%1.1f%%", startangle=90)
            ax.set_title("Human Review Decisions", fontsize=11, fontweight="bold")
        else:
            ax.text(0.5, 0.5, "No reviews yet", ha="center", va="center", transform=ax.transAxes)
            ax.set_title("Human Review Decisions")

    # Verified vs unverified
    ax2 = axes[1]
    if "human_verified" in df.columns:
        verified = df["human_verified"].sum()
        total = len(df)
        unverified = total - verified
        ax2.bar(["Human Verified", "Pending Review"], [verified, unverified],
                color=["#27ae60", "#95a5a6"])
        ax2.set_title("Review Status", fontsize=11, fontweight="bold")
        ax2.set_ylabel("Lead Count")

    plt.tight_layout()
    path = out_dir / "05_review_summary.png"
    plt.savefig(path, dpi=150)
    plt.close()
    log.info("Saved: %s", path)


def generate_summary_table(df: pd.DataFrame, out_dir: Path):
    """Save a styled HTML summary table."""
    score_col = "final_score" if "final_score" in df.columns else "icp_score"
    cols = [c for c in ["business_name", "category", score_col, "risk_level",
                        "website_status", "booking_present", "has_seo", "social_count",
                        "human_action", "human_verified"] if c in df.columns]
    subset = df[cols].sort_values(score_col, ascending=False) if score_col in df.columns else df[cols]

    html = subset.to_html(index=False, border=1, classes="leads-table")
    page = f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<title>ICP Lead Summary</title>
<style>
  body {{ font-family: sans-serif; margin: 2rem; }}
  .leads-table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
  .leads-table th {{ background: #2c3e50; color: white; padding: 8px; text-align: left; }}
  .leads-table td {{ padding: 6px 8px; border-bottom: 1px solid #ddd; }}
  .leads-table tr:nth-child(even) {{ background: #f8f9fa; }}
</style>
</head><body>
<h1>ICP Lead Generation Summary</h1>
<p>Total leads: {len(df)} | Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}</p>
{html}
</body></html>"""

    path = out_dir / "leads_summary.html"
    path.write_text(page)
    log.info("Saved summary table: %s", path)


def main():
    parser = argparse.ArgumentParser(description="Generate ICP lead visualization dashboard")
    parser.add_argument("--csv", default=None, help="Scored leads CSV path")
    parser.add_argument("--json", default=None, help="Scored leads JSON path")
    parser.add_argument("--out", default=None, help="Output directory for charts")
    parser.add_argument("--charts", nargs="*",
                        choices=["distribution", "category", "high_risk", "correlation", "review", "all"],
                        default=["all"])
    args = parser.parse_args()

    out_dir = Path(args.out) if args.out else OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    setup_style()

    try:
        df = load_data(scored_csv=args.csv, scored_json=args.json)
    except FileNotFoundError as e:
        log.error(str(e))
        return

    run_all = "all" in (args.charts or ["all"])

    if run_all or "distribution" in args.charts:
        plot_score_distribution(df, out_dir)
    if run_all or "category" in args.charts:
        plot_category_breakdown(df, out_dir)
    if run_all or "high_risk" in args.charts:
        plot_high_risk_leads(df, out_dir)
    if run_all or "correlation" in args.charts:
        plot_digital_presence_correlation(df, out_dir)
    if run_all or "review" in args.charts:
        plot_review_summary(df, out_dir)

    generate_summary_table(df, out_dir)

    print(f"\nDashboard generated in: {out_dir}")
    print("Files:")
    for f in sorted(out_dir.iterdir()):
        print(f"  {f.name}")


if __name__ == "__main__":
    main()

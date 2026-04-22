"""
Lead collector using DuckDuckGo HTML search (no API key required).
Extracts business name, address, category, website from search results.
"""

import re
import time
import json
import logging
import argparse
from pathlib import Path
from urllib.parse import urlparse, quote_plus

import requests
from bs4 import BeautifulSoup

from sources import CATEGORY_QUERIES

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
DDG_URL = "https://html.duckduckgo.com/html/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Accept-Language": "en-US,en;q=0.9",
}


def ddg_search(query: str, max_results: int = 10, pause: float = 2.0) -> list[dict]:
    """Fetch DuckDuckGo HTML search results for a query."""
    results = []
    try:
        resp = requests.post(
            DDG_URL,
            data={"q": query, "b": "", "kl": "us-en"},
            headers=HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        for result in soup.select(".result"):
            title_el = result.select_one(".result__title a")
            snippet_el = result.select_one(".result__snippet")
            url_el = result.select_one(".result__url")

            if not title_el:
                continue

            href = title_el.get("href", "")
            # DDG wraps links — extract real URL
            url = _extract_real_url(href)
            snippet = snippet_el.get_text(strip=True) if snippet_el else ""
            displayed_url = url_el.get_text(strip=True) if url_el else url

            results.append({
                "title": title_el.get_text(strip=True),
                "url": url,
                "snippet": snippet,
                "displayed_url": displayed_url,
            })
            if len(results) >= max_results:
                break
    except Exception as e:
        log.warning("DDG search error for '%s': %s", query, e)

    time.sleep(pause)
    return results


def _extract_real_url(href: str) -> str:
    """DDG wraps URLs in redirects — try to extract the real destination."""
    if href.startswith("http") and "duckduckgo.com" not in href:
        return href
    # Try to find uddg= param
    m = re.search(r"uddg=([^&]+)", href)
    if m:
        from urllib.parse import unquote
        return unquote(m.group(1))
    return href


def parse_lead_from_result(result: dict, category: str, zip_code: str) -> dict | None:
    """
    Attempt to extract a structured lead record from a single search result.
    Returns None if the result doesn't look like a local business.
    """
    url = result.get("url", "")
    if not url or _is_junk_url(url):
        return None

    # Heuristic: skip aggregators/directories
    aggregators = ["yelp.com", "healthgrades.com", "vitals.com", "zocdoc.com",
                   "webmd.com", "wikipedia.org", "npi.io", "yellowpages.com"]
    parsed = urlparse(url)
    if any(a in parsed.netloc for a in aggregators):
        return None

    title = result.get("title", "").strip()
    snippet = result.get("snippet", "")

    # Try to extract address from snippet
    address = _extract_address(snippet) or f"Near {zip_code}"
    geo_area = f"ZIP {zip_code}"

    return {
        "business_name": title,
        "website": url,
        "category": CATEGORY_QUERIES.get(category, {}).get("label", category),
        "geo_area": geo_area,
        "address": address,
        "phone": _extract_phone(snippet),
        "email": None,
        "source": "duckduckgo",
        "raw_snippet": snippet,
    }


def _is_junk_url(url: str) -> bool:
    if not url.startswith("http"):
        return True
    junk = ["javascript:", "mailto:", "#", "google.com/search"]
    return any(j in url for j in junk)


def _extract_address(text: str) -> str | None:
    """Simple regex to pull street-like addresses from snippet text."""
    pattern = r"\d+\s+[A-Z][a-zA-Z\s]+(St|Ave|Rd|Blvd|Dr|Pkwy|Way|Ln|Ct|Pl|Suite|Ste)[^\n,]{0,60}"
    m = re.search(pattern, text)
    return m.group(0).strip() if m else None


def _extract_phone(text: str) -> str | None:
    m = re.search(r"\(?\d{3}\)?[\s\-\.]\d{3}[\s\-\.]\d{4}", text)
    return m.group(0).strip() if m else None


def collect_leads(
    zip_code: str = "30350",
    category: str = "healthcare",
    max_per_query: int = 10,
    pause: float = 2.0,
) -> list[dict]:
    """
    Run all queries for a given category and zip code.
    Returns deduplicated list of lead dicts.
    """
    cat_config = CATEGORY_QUERIES.get(category)
    if not cat_config:
        log.error("Unknown category: %s. Available: %s", category, list(CATEGORY_QUERIES.keys()))
        return []

    seen_urls: set[str] = set()
    leads: list[dict] = []

    for query_tpl in cat_config["queries"]:
        query = query_tpl.format(zip=zip_code)
        log.info("Searching: %s", query)
        results = ddg_search(query, max_results=max_per_query, pause=pause)

        for r in results:
            lead = parse_lead_from_result(r, category, zip_code)
            if lead and lead["website"] not in seen_urls:
                seen_urls.add(lead["website"])
                leads.append(lead)

    log.info("Collected %d unique leads for ZIP %s / category '%s'", len(leads), zip_code, category)
    return leads


def main():
    parser = argparse.ArgumentParser(description="Collect local business leads via DuckDuckGo")
    parser.add_argument("--zip", default="30350", help="ZIP code to search near")
    parser.add_argument("--category", default="healthcare", help="Business category")
    parser.add_argument("--max", type=int, default=10, help="Max results per query")
    parser.add_argument("--pause", type=float, default=2.0, help="Pause seconds between requests")
    parser.add_argument("--out", default=None, help="Output JSON file path")
    args = parser.parse_args()

    leads = collect_leads(
        zip_code=args.zip,
        category=args.category,
        max_per_query=args.max,
        pause=args.pause,
    )

    out_path = args.out or str(ROOT / "data" / "raw_leads.json")
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    # Merge with existing if file exists
    existing = []
    if Path(out_path).exists():
        with open(out_path) as f:
            existing = json.load(f)

    existing_urls = {l.get("website") for l in existing}
    new_leads = [l for l in leads if l["website"] not in existing_urls]
    all_leads = existing + new_leads

    with open(out_path, "w") as f:
        json.dump(all_leads, f, indent=2)

    log.info("Saved %d total leads (%d new) → %s", len(all_leads), len(new_leads), out_path)


if __name__ == "__main__":
    main()

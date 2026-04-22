"""
Google Business Profile signal extractor.
Uses DuckDuckGo search snippets to infer GBP signals without an API key.
All extraction is best-effort; values may be None when not detectable.
"""

import re
import time
import logging
import requests
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

DDG_URL = "https://html.duckduckgo.com/html/"
DDG_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

_RATING_PATTERNS = [
    re.compile(r'(\d+\.\d+)\s*(?:stars?|★|out\s+of\s+5)', re.IGNORECASE),
    re.compile(r'Rated\s+(\d+\.\d+)', re.IGNORECASE),
    re.compile(r'(\d+\.\d+)\s*[·\|]\s*\d+\s+(?:review|rating)', re.IGNORECASE),
    re.compile(r'(\d+\.\d+)\s*\(\d+\)', re.IGNORECASE),
]

_REVIEW_PATTERNS = [
    re.compile(r'(\d{1,4}(?:,\d{3})*)\s+(?:Google\s+)?(?:review|rating)s', re.IGNORECASE),
    re.compile(r'\((\d{1,4}(?:,\d{3})*)\s+(?:review|rating)s?\)', re.IGNORECASE),
    re.compile(r'[·|]\s*(\d{1,4}(?:,\d{3})*)\s+(?:review|rating)', re.IGNORECASE),
]


def get_gbp_signals(
    business_name: str,
    zip_code: str = "",
    address: str = "",
    pause: float = 2.0,
    timeout: int = 10,
) -> dict:
    """
    Search DuckDuckGo for Google Business Profile signals for the given business.

    Returns a dict with:
      gbp_rating       - float 1.0-5.0 or None
      gbp_review_count - int or None
      gbp_photo_count  - int or None (rarely detectable from snippets)
      gbp_verified     - bool (True if rating+reviews found)
      gbp_unclaimed    - bool (True if no reviews/rating detected)
    """
    result = {
        "gbp_rating": None,
        "gbp_review_count": None,
        "gbp_photo_count": None,
        "gbp_verified": False,
        "gbp_unclaimed": False,
    }

    query = f'"{business_name}" {zip_code} google reviews rating'

    try:
        resp = requests.post(
            DDG_URL,
            data={"q": query, "b": "", "kl": "us-en"},
            headers=DDG_HEADERS,
            timeout=timeout,
        )
        if resp.status_code != 200:
            log.debug("DDG returned %d for GBP query: %s", resp.status_code, business_name)
            return result

        soup = BeautifulSoup(resp.text, "html.parser")
        snippets = [s.get_text(separator=" ") for s in soup.select(".result__snippet")]
        titles = [t.get_text(separator=" ") for t in soup.select(".result__a")]
        all_text = " ".join(snippets + titles)

        # Extract rating
        for pat in _RATING_PATTERNS:
            m = pat.search(all_text)
            if m:
                try:
                    rating = float(m.group(1))
                    if 1.0 <= rating <= 5.0:
                        result["gbp_rating"] = round(rating, 1)
                        break
                except ValueError:
                    pass

        # Extract review count
        for pat in _REVIEW_PATTERNS:
            m = pat.search(all_text)
            if m:
                try:
                    count = int(m.group(1).replace(",", ""))
                    if count >= 0:
                        result["gbp_review_count"] = count
                        break
                except ValueError:
                    pass

        # Derive verified and unclaimed flags
        has_rating = result["gbp_rating"] is not None
        has_reviews = result["gbp_review_count"] is not None and result["gbp_review_count"] > 0

        if has_rating and has_reviews:
            result["gbp_verified"] = True
        elif not has_rating and not has_reviews:
            result["gbp_unclaimed"] = True
        elif result["gbp_review_count"] == 0:
            result["gbp_unclaimed"] = True

        log.debug(
            "GBP signals for '%s': rating=%s reviews=%s verified=%s unclaimed=%s",
            business_name,
            result["gbp_rating"],
            result["gbp_review_count"],
            result["gbp_verified"],
            result["gbp_unclaimed"],
        )

    except requests.exceptions.Timeout:
        log.debug("GBP lookup timed out for %s", business_name)
    except Exception as e:
        log.debug("GBP lookup failed for %s: %s", business_name, e)

    time.sleep(pause)
    return result


def enrich_leads_gbp(
    leads: list[dict],
    pause: float = 2.0,
    timeout: int = 10,
) -> list[dict]:
    """
    Add GBP signals to a list of leads in-place.
    Modifies each lead's 'enrichment' sub-dict directly.
    """
    total = len(leads)
    for i, lead in enumerate(leads, 1):
        name = lead.get("business_name") or lead.get("name", "?")
        zip_code = (lead.get("geo_area") or lead.get("zip_code") or "").replace("ZIP ", "").strip()
        address = lead.get("address", "")

        log.info("[%d/%d] GBP lookup: %s", i, total, name)
        signals = get_gbp_signals(name, zip_code=zip_code, address=address, pause=pause, timeout=timeout)

        if "enrichment" not in lead or lead["enrichment"] is None:
            lead["enrichment"] = {}
        lead["enrichment"].update(signals)

    return leads

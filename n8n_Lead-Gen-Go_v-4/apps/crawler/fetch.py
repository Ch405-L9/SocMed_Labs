"""
Website enrichment crawler.
Fetches each lead's website and extracts digital presence signals,
phone numbers, emails (with MX verification), and optional PageSpeed scores.
"""

import json
import logging
import argparse
import hashlib
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

try:
    import trafilatura
    HAS_TRAFILATURA = True
except ImportError:
    HAS_TRAFILATURA = False

try:
    import dns.resolver
    HAS_DNSPYTHON = True
except ImportError:
    HAS_DNSPYTHON = False

from sources import BOOKING_SIGNALS, CONTACT_FORM_SIGNALS, SOCIAL_DOMAINS, SEO_QUALITY_SIGNALS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

PAGESPEED_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"


def content_hash(html: str) -> str:
    """Return a 16-character sha256 hex digest of the page HTML."""
    return hashlib.sha256(html.encode("utf-8", errors="replace")).hexdigest()[:16]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

_PHONE_RE = re.compile(r"\(?\d{3}\)?[\s\-\.]\d{3}[\s\-\.]\d{4}")
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")

# Domains that commonly appear in page source but are not contact emails
_EMAIL_BLACKLIST = {
    "example.com", "sentry.io", "schema.org", "w3.org", "googleapis.com",
    "cloudflare.com", "jquery.com", "bootstrapcdn.com", "fontawesome.com",
    "wixpress.com", "squarespace.com", "shopify.com", "wordpress.org",
}


def verify_mx(domain: str) -> bool:
    """Return True if the domain has MX records (can receive email)."""
    if not HAS_DNSPYTHON:
        return True  # Assume valid if dnspython not installed
    try:
        dns.resolver.resolve(domain, "MX", lifetime=5)
        return True
    except Exception:
        return False


def get_pagespeed_scores(url: str, api_key: str = "", strategy: str = "mobile", timeout: int = 30) -> dict:
    """
    Call the Google PageSpeed Insights API (v5) for the given URL.
    Returns performance, seo, and accessibility scores (0-100), or empty dict on failure.
    Free tier: ~400 requests/day/IP without an API key.
    """
    params = {
        "url": url,
        "strategy": strategy,
        "category": ["performance", "seo", "accessibility"],
    }
    if api_key:
        params["key"] = api_key

    try:
        resp = requests.get(PAGESPEED_URL, params=params, timeout=timeout)
        if resp.status_code != 200:
            log.debug("PageSpeed API returned %d for %s", resp.status_code, url)
            return {}
        data = resp.json()
        cats = data.get("lighthouseResult", {}).get("categories", {})
        return {
            "pagespeed_performance": round((cats.get("performance", {}).get("score") or 0) * 100),
            "pagespeed_seo": round((cats.get("seo", {}).get("score") or 0) * 100),
            "pagespeed_accessibility": round((cats.get("accessibility", {}).get("score") or 0) * 100),
        }
    except Exception as e:
        log.debug("PageSpeed call failed for %s: %s", url, e)
        return {}


def fetch_website(
    url: str,
    timeout: int = 10,
    retries: int = 2,
    extract_contacts: bool = True,
    use_pagespeed: bool = False,
    pagespeed_api_key: str = "",
    pagespeed_strategy: str = "mobile",
    pagespeed_timeout: int = 30,
    use_playwright: bool = False,
) -> dict:
    """
    Fetch a URL and return an enrichment dict with digital presence signals,
    extracted phone/email contacts, and optional PageSpeed scores.
    """
    result = {
        "url": url,
        "website_status": "unknown",
        "http_code": None,
        "is_https": url.startswith("https://"),
        "booking_present": False,
        "contact_form": False,
        "seo_title": None,
        "seo_description": None,
        "has_seo": False,
        "social_links": [],
        "social_count": 0,
        "page_summary": None,
        "raw_html_len": 0,
        "phone_numbers": [],
        "primary_phone": None,
        "email_addresses": [],
        "primary_email": None,
        "mx_verified": False,
        "pagespeed_performance": None,
        "pagespeed_seo": None,
        "pagespeed_accessibility": None,
        "last_crawled": None,
        "content_hash": None,
        "gbp_rating": None,
        "gbp_review_count": None,
        "gbp_photo_count": None,
        "gbp_verified": False,
        "gbp_unclaimed": False,
    }

    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
            result["http_code"] = resp.status_code
            result["is_https"] = resp.url.startswith("https://")

            if resp.status_code == 200:
                result["website_status"] = "reachable"
                result["last_crawled"] = utc_now_iso()
                result["content_hash"] = content_hash(resp.text)
                _parse_html(resp.text, result)
                if extract_contacts:
                    _extract_contacts(resp.text, result)
            elif resp.status_code in (403, 429):
                result["website_status"] = "blocked"
            elif resp.status_code == 404:
                result["website_status"] = "not_found"
            else:
                result["website_status"] = f"error_{resp.status_code}"
            break

        except requests.exceptions.SSLError:
            result["website_status"] = "ssl_error"
            result["is_https"] = False
            break
        except requests.exceptions.ConnectionError as e:
            if "NameResolutionError" in str(e) or "Name or service not known" in str(e):
                result["website_status"] = "dns_failed"
                break
            result["website_status"] = "connection_error"
            if attempt < retries:
                time.sleep(1)
        except requests.exceptions.Timeout:
            result["website_status"] = "timeout"
            if attempt < retries:
                time.sleep(1)
        except Exception as e:
            result["website_status"] = "exception"
            result["error"] = str(e)[:200]
            break

    # Playwright retry for blocked sites (403/blocked status)
    if use_playwright and result["website_status"] in ("blocked", "connection_error"):
        log.info("Retrying %s with Playwright ...", url)
        try:
            from render import render_page
            html = render_page(url, timeout=timeout)
            if html:
                result["website_status"] = "reachable_via_browser"
                result["last_crawled"] = utc_now_iso()
                result["content_hash"] = content_hash(html)
                _parse_html(html, result)
                if extract_contacts:
                    _extract_contacts(html, result)
                log.info("Playwright recovered content for %s (%d chars)", url, len(html))
        except Exception as e:
            log.debug("Playwright retry failed for %s: %s", url, e)

    if use_pagespeed and result["website_status"] in ("reachable", "reachable_via_browser"):
        scores = get_pagespeed_scores(
            url,
            api_key=pagespeed_api_key,
            strategy=pagespeed_strategy,
            timeout=pagespeed_timeout,
        )
        result.update(scores)

    return result


def _parse_html(html: str, result: dict):
    """Extract presence signals from page HTML into result dict."""
    soup = BeautifulSoup(html, "html.parser")
    text_lower = html.lower()

    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else ""
    desc_meta = soup.find("meta", attrs={"name": "description"})
    og_title = soup.find("meta", property="og:title")
    og_desc = soup.find("meta", property="og:description")

    result["seo_title"] = title[:200] if title else None
    result["seo_description"] = (
        desc_meta.get("content", "")[:300]
        if desc_meta else
        og_desc.get("content", "")[:300] if og_desc else None
    )

    weak = any(w in title.lower() for w in SEO_QUALITY_SIGNALS["weak_indicators"])
    result["has_seo"] = bool(title and not weak and (desc_meta or og_desc or og_title))

    result["booking_present"] = any(sig in text_lower for sig in BOOKING_SIGNALS)
    result["contact_form"] = any(sig in text_lower for sig in CONTACT_FORM_SIGNALS)

    socials = []
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        for platform, domain in SOCIAL_DOMAINS.items():
            if domain in href and href not in socials:
                socials.append(href)
                break
    result["social_links"] = socials[:10]
    result["social_count"] = len(result["social_links"])

    if HAS_TRAFILATURA:
        text = trafilatura.extract(html, no_fallback=False, include_links=False)
        if text:
            result["page_summary"] = text[:1000]
    else:
        body = soup.find("body")
        if body:
            raw = body.get_text(separator=" ", strip=True)
            result["page_summary"] = raw[:1000] if raw else None

    result["raw_html_len"] = len(html)


def _extract_contacts(html: str, result: dict):
    """
    Extract phone numbers and email addresses from page HTML.
    Verifies email domains via MX lookup before including.
    Updates result dict in-place.
    """
    soup = BeautifulSoup(html, "html.parser")
    visible_text = soup.get_text(separator=" ")

    # Phone numbers — from visible text and tel: links
    phones: list[str] = []
    for tag in soup.find_all("a", href=True):
        href = tag["href"]
        if href.startswith("tel:"):
            number = re.sub(r"[^\d+\-\(\)\s]", "", href[4:]).strip()
            if number and number not in phones:
                phones.append(number)

    for m in _PHONE_RE.finditer(visible_text):
        num = m.group(0).strip()
        if num not in phones:
            phones.append(num)

    result["phone_numbers"] = phones[:5]
    result["primary_phone"] = phones[0] if phones else None

    # Emails — from mailto: links first, then regex on visible text
    raw_emails: list[str] = []
    for tag in soup.find_all("a", href=True):
        href = tag["href"]
        if href.startswith("mailto:"):
            addr = href[7:].split("?")[0].strip().lower()
            if addr and addr not in raw_emails:
                raw_emails.append(addr)

    for m in _EMAIL_RE.finditer(visible_text):
        addr = m.group(0).lower()
        if addr not in raw_emails:
            raw_emails.append(addr)

    # Filter blacklisted domains and verify MX
    verified: list[str] = []
    mx_passed = False
    seen_domains: dict[str, bool] = {}

    for addr in raw_emails[:20]:
        parts = addr.rsplit("@", 1)
        if len(parts) != 2:
            continue
        domain = parts[1]
        if domain in _EMAIL_BLACKLIST:
            continue
        if domain not in seen_domains:
            seen_domains[domain] = verify_mx(domain)
        if seen_domains[domain]:
            verified.append(addr)
            mx_passed = True
        if len(verified) >= 5:
            break

    result["email_addresses"] = verified
    result["primary_email"] = verified[0] if verified else None
    result["mx_verified"] = mx_passed


def enrich_leads(
    leads: list[dict],
    timeout: int = 10,
    pause: float = 1.0,
    extract_contacts: bool = True,
    use_pagespeed: bool = False,
    pagespeed_api_key: str = "",
    pagespeed_strategy: str = "mobile",
    pagespeed_timeout: int = 30,
    crawl_cache: dict = None,
    crawl_window_days: int = 7,
    force_crawl: bool = False,
    use_playwright: bool = False,
) -> list[dict]:
    """
    Enrich a list of lead dicts with website crawl data.

    crawl_cache: dict of url -> {last_crawled, content_hash} for incremental mode.
    crawl_window_days: skip leads crawled within this many days (0 = always crawl).
    force_crawl: bypass all cache checks.
    """
    from datetime import datetime, timezone, timedelta

    enriched = []
    total = len(leads)
    skipped = 0

    for i, lead in enumerate(leads, 1):
        url = lead.get("website") or lead.get("url")
        name = lead.get("business_name") or lead.get("name", "?")

        # Check incremental cache
        existing_enrichment = lead.get("enrichment") or {}
        cached = (crawl_cache or {}).get(url) or {}
        last_crawled_str = cached.get("last_crawled") or existing_enrichment.get("last_crawled")
        prev_hash = cached.get("content_hash") or existing_enrichment.get("content_hash")

        if not force_crawl and url and last_crawled_str and crawl_window_days > 0:
            try:
                last_crawled = datetime.fromisoformat(last_crawled_str.replace("Z", "+00:00"))
                age = datetime.now(timezone.utc) - last_crawled
                if age < timedelta(days=crawl_window_days):
                    log.info("[%d/%d] SKIP (crawled %dd ago): %s", i, total, age.days, name)
                    skipped += 1
                    enriched.append({**lead, "enrichment": existing_enrichment or {"website_status": "cached"}})
                    continue
            except (ValueError, TypeError):
                pass

        log.info("[%d/%d] Crawling: %s — %s", i, total, name, url)

        if not url:
            crawl = {"website_status": "no_url"}
        else:
            crawl = fetch_website(
                url,
                timeout=timeout,
                extract_contacts=extract_contacts,
                use_pagespeed=use_pagespeed,
                pagespeed_api_key=pagespeed_api_key,
                pagespeed_strategy=pagespeed_strategy,
                pagespeed_timeout=pagespeed_timeout,
                use_playwright=use_playwright,
            )

            # Detect unchanged content — carry over existing enrichment where possible
            new_hash = crawl.get("content_hash")
            if new_hash and prev_hash and new_hash == prev_hash and existing_enrichment:
                log.info("  Content unchanged (hash match) — reusing prior enrichment for %s", name)
                crawl = {**existing_enrichment, "last_crawled": crawl["last_crawled"], "content_hash": new_hash}

        # Propagate extracted contacts up to lead level if not already set
        if not lead.get("phone") and crawl.get("primary_phone"):
            lead["phone"] = crawl["primary_phone"]
        if not lead.get("email") and crawl.get("primary_email"):
            lead["email"] = crawl["primary_email"]

        merged = {**lead, "enrichment": crawl}
        enriched.append(merged)
        time.sleep(pause)

    if skipped:
        log.info("Incremental crawl: %d leads skipped (within %d-day window)", skipped, crawl_window_days)

    return enriched


def main():
    parser = argparse.ArgumentParser(description="Crawl websites and extract enrichment signals")
    parser.add_argument("--in", dest="infile", default=None, help="Input JSON leads file")
    parser.add_argument("--out", default=None, help="Output enriched JSON file")
    parser.add_argument("--timeout", type=int, default=10)
    parser.add_argument("--pause", type=float, default=1.0)
    parser.add_argument("--no-contacts", action="store_true", help="Skip phone/email extraction")
    parser.add_argument("--pagespeed", action="store_true", help="Call PageSpeed Insights API")
    parser.add_argument("--pagespeed-key", default="", help="Google API key for PageSpeed")
    args = parser.parse_args()

    in_path = args.infile or str(ROOT / "data" / "raw_leads.json")
    out_path = args.out or str(ROOT / "data" / "enriched_leads.json")

    if not Path(in_path).exists():
        alt = ROOT / "data" / "analyzed_leads.json"
        if alt.exists():
            log.info("No raw_leads.json — using existing analyzed_leads.json")
            in_path = str(alt)
        else:
            log.error("Input file not found: %s", in_path)
            return

    with open(in_path) as f:
        leads = json.load(f)

    for lead in leads:
        if "name" in lead and "business_name" not in lead:
            lead["business_name"] = lead.pop("name")
        if "url" in lead and "website" not in lead:
            lead["website"] = lead.pop("url")

    enriched = enrich_leads(
        leads,
        timeout=args.timeout,
        pause=args.pause,
        extract_contacts=not args.no_contacts,
        use_pagespeed=args.pagespeed,
        pagespeed_api_key=args.pagespeed_key,
    )

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(enriched, f, indent=2)

    log.info("Enriched %d leads → %s", len(enriched), out_path)


if __name__ == "__main__":
    main()

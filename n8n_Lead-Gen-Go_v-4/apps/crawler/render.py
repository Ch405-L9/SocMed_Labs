"""
Optional Playwright-based renderer for JavaScript-heavy pages.
Only used when config.crawler.use_playwright = true.
Falls back gracefully if playwright is not installed.
"""

import logging

log = logging.getLogger(__name__)


def render_page(url: str, timeout: int = 20) -> str | None:
    """
    Render a page using Playwright and return the full HTML.
    Returns None if Playwright is not installed or rendering fails.
    """
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except ImportError:
        log.warning("Playwright not installed. Install with: pip install playwright && playwright install chromium")
        return None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
            )
            page.goto(url, timeout=timeout * 1000, wait_until="networkidle")
            html = page.content()
            browser.close()
            return html
    except Exception as e:
        log.warning("Playwright render failed for %s: %s", url, e)
        return None

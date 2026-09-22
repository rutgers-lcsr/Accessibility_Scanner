
import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, TypedDict
from scanner.accessibility.ace import AxeReport, get_accessibility_report
from scanner.browser.parse import  get_documents, get_imgs, get_links, get_videos
from playwright.async_api import Browser
import time 
from scanner.browser.tabbable import is_page_tabbable
from scanner.browser.wait import wait_for_page_settled
from scanner.log import log_message
from utils.style_generator import report_to_js
from utils.urls import get_netloc, get_website_url, is_safe_target

ACCESSIBILITY_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3 LCSRAccessibility/1.0"


async def block_non_public_targets(route):
    """Playwright route handler: abort any request whose host is not public.

    The browser runs inside the compose network, so without this a redirect or a
    subresource on a scanned page could reach internal services (database, redis,
    cloud metadata). DNS is resolved off the event loop and cached per host.
    """
    url = route.request.url
    if url.startswith(("http://", "https://")):
        loop = asyncio.get_running_loop()
        if not await loop.run_in_executor(None, is_safe_target, url):
            log_message(f"Blocked request to non-public target: {url}", 'warning')
            await route.abort()
            return
    await route.continue_()


def _same_host(url_a: str, url_b: str) -> bool:
    """True when both URLs are on the same host, ignoring a leading ``www.``."""
    def bare(url):
        host = get_netloc(url).lower()
        return host[4:] if host.startswith("www.") else host
    return bare(url_a) == bare(url_b)

class AccessibilityReport(TypedDict, total=False):
    url: str
    response_code: int
    error: str
    base_url: str
    report: AxeReport
    links: List[str]
    documents: List[str]
    videos: List[str]
    imgs: List[str]
    tabable: bool
    timestamp: str
    photo: bytes
    tags: List[str]
    
@dataclass
class AccessibilitySummary:
    """
    A lightweight summary of one page's report. The crawler keeps one of these per page
    instead of the full AccessibilityReport (which includes the screenshot bytes), so a
    large website does not hold every report in memory for the whole scan.
    """
    url: str
    response_code: int = 0
    error: str = ''
    base_url: str = ''

    @classmethod
    def from_report(cls, report: AccessibilityReport) -> 'AccessibilitySummary':
        return cls(
            url=report.get('url', ''),
            response_code=report.get('response_code', 0) or 0,
            error=report.get('error', '') or '',
            base_url=report.get('base_url', ''),
        )


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# Generates a AccessibilityReport for a given site
async def generate_report(browser: Browser, website: str = "https://cs.rutgers.edu", tags: List[str] = [], ace_config: str = "") -> AccessibilityReport:
    """Audit one page.

    Always returns a report carrying ``url`` and ``timestamp``; on failure ``error`` is set
    and the other fields are absent. The browser context (and with it the page) is closed
    on every path, including exceptions and cancellation.
    """
    result = AccessibilityReport(url=website, timestamp=_now())
    try:
        async with await browser.new_context(user_agent=ACCESSIBILITY_USER_AGENT) as context:
            await context.route("**/*", block_non_public_targets)
            page = await context.new_page()
            res = await page.goto(website, wait_until="domcontentloaded")
            result['response_code'] = res.status if res else 0
            if res is None or res.status >= 400:
                result['error'] = f"Failed to load page, status code: {res.status if res else 'No Response'}"
                return result
            # A page that redirected to another host must not be audited under this URL.
            if not _same_host(page.url, website):
                result['error'] = f"Redirected off-site to {page.url}"
                return result
            await wait_for_page_settled(page)

            base_url = get_website_url(page.url)
            report = await get_accessibility_report(page, tags=tags, axe_config=ace_config)
            if 'error' in report and report['error'] is not None:
                result['error'] = report['error']
                return result
            links = await get_links(page)
            documents = await get_documents(page)
            videos = await get_videos(page)
            imgs = await get_imgs(page)
            tabable = await is_page_tabbable(page)

            js_report = report_to_js(report['violations'], page.url, report_mode=True)
            await page.evaluate(f"(function () {{ {js_report} }})()")
            photo = await page.screenshot(full_page=True)

            result['base_url'] = base_url
            result['report'] = report
            result['links'] = links
            result['documents'] = documents
            result['videos'] = videos
            result['imgs'] = imgs
            result['tabable'] = tabable
            result['timestamp'] = _now()
            result['photo'] = photo
            result['tags'] = tags or []
            return result
    except Exception as e:
        log_message(f"Error generating report for {website}: {e}", 'error')
        result['error'] = str(e)
        return result

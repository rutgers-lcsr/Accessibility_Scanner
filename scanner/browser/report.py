
import asyncio
from datetime import datetime, timezone
from typing import List, TypedDict
from scanner.accessibility.ace import AxeReport, get_accessibility_report
from scanner.browser.parse import  get_imgs, get_links, get_videos
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
    videos: List[str]
    imgs: List[str]
    tabable: bool
    timestamp: str
    photo: bytes
    tags: List[str]
    
class AccessibilitySummary(TypedDict, total=False):
    """
    A summary of the accessibility report for a given URL.
    this is a lightweight version of the full AccessibilityReport. 
    
    to prevent large websites from consuming too much memory when storing multiple reports. 
    """
    def __init__(self, accessibility_report: AccessibilityReport):
        self.url: str = accessibility_report.get('url', '')
        self.response_code: int = accessibility_report.get('response_code', 0)
        self.error: str = accessibility_report.get('error', '')
        self.base_url: str = accessibility_report.get('base_url', '')



# Generates a AccessibilityReport for a given site
async def generate_report(browser: Browser, website: str = "https://cs.rutgers.edu", tags: List[str] = [], ace_config: str = "") -> AccessibilityReport:
    result = AccessibilityReport()
    result['timestamp'] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        context = await browser.new_context(user_agent=ACCESSIBILITY_USER_AGENT)
        await context.route("**/*", block_non_public_targets)
        page = await context.new_page()
        res = await page.goto(website, wait_until="domcontentloaded")
        result['url'] = website
        result['response_code'] = res.status if res else 0
        if res is None or res.status >= 400:
            await page.close()
            result['error'] = f"Failed to load page, status code: {res.status if res else 'No Response'}"
            return result
        # A page that redirected to another host must not be audited under this URL.
        if not _same_host(page.url, website):
            await page.close()
            result['error'] = f"Redirected off-site to {page.url}"
            return result
        await wait_for_page_settled(page)
    except Exception as e:
        return {"error": str(e)}

    try:
        base_url = get_website_url(page.url)
        report = await get_accessibility_report(page, tags=tags, axe_config=ace_config)
        if 'error' in report and report['error'] is not None:
            await page.close()
            return {"error": report['error']}
        links = await get_links(page)
        videos = await get_videos(page)
        imgs = await get_imgs(page)

        tabable = await is_page_tabbable(page)
        has_video = await page.evaluate("() => { return !!document.querySelector('video'); }")
        has_img = await page.evaluate("() => { return !!document.querySelector('img'); }")
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        js_report = report_to_js(report['violations'], page.url, report_mode=True)
        context = await page.evaluate(f"(function () {{ {js_report} }})()")
        
        photo = await page.screenshot(full_page=True)

        await page.close()
        # Process the report as needed
        
        result['base_url'] = base_url
        result['report'] = report
        result['links'] = links
        result['videos'] = videos
        result['imgs'] = imgs
        result['tabable'] = tabable
        result['has_video'] = has_video
        result['has_img'] = has_img
        result['timestamp'] = timestamp
        result['photo'] = photo
        result['tags'] = tags or []

        return result
    except Exception as e:
        await page.close()
        log_message(f"Error generating report for {website}: {e}", 'error')
        return {"error": str(e)}
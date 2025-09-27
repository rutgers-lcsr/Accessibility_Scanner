
from typing import List, TypedDict
from scanner.accessibility.ace import AxeReport, get_accessibility_report
from scanner.browser.parse import  get_imgs, get_links, get_videos
from playwright.async_api import Browser
import time 
from scanner.browser.tabbable import is_page_tabbable
from scanner.log import log_message
from utils.style_generator import report_to_js
from utils.urls import get_website_url
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
    timestamp: float
    photo: bytes
    tags: List[str]
    
    



# Generates a AccessibilityReport for a given site
async def generate_report(browser: Browser, website: str = "https://cs.rutgers.edu", tags: List[str] = [], ace_config: str = "") -> AccessibilityReport:
    result = AccessibilityReport()
    result['timestamp'] = time.time()
    try:
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3 LCSRAccessibility/1.0")
        page = await context.new_page()
        res = await page.goto(website)
        result['url'] = website
        result['response_code'] = res.status if res else 0
        if res is None or res.status >= 400:
            await page.close()
            result['error'] = f"Failed to load page, status code: {res.status if res else 'No Response'}"
            return result
        await page.wait_for_load_state()
        await page.wait_for_timeout(1000)  # Wait for a second to ensure the page is fully loaded
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
        timestamp = time.time()

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
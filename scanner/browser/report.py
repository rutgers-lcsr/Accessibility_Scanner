
from typing import List, TypedDict
from scanner.accessibility.ace import AxeReport, get_accessibility_report
from scanner.browser.parse import  get_imgs, get_links, get_videos
from playwright.async_api import Browser
import time 
from scanner.browser.tabbable import is_page_tabbable
from utils.style_generator import report_to_js
from utils.urls import get_website_url

class AccessibilityReport(TypedDict, total=False):
    url: str
    base_url: str
    report: AxeReport
    links: List[str]
    videos: List[str]
    imgs: List[str]
    tabable: bool
    timestamp: float
    photo: bytes



# Generates a AccessibilityReport for a given site
async def generate_report(browser: Browser, website: str = "https://cs.rutgers.edu")-> AccessibilityReport:
    try:
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3 LCSRAccessibility/1.0")
        page = await context.new_page()
        await page.goto(website)
        await page.wait_for_load_state('networkidle')
    except Exception as e:
        return {"error": str(e)}

    base_url = get_website_url(page.url)
    report = await get_accessibility_report(page)

    links = await get_links(page)

    videos = await get_videos(page)
    
    imgs = await get_imgs(page)

    tabable = await is_page_tabbable(page)
    has_video = await page.evaluate("() => { return !!document.querySelector('video'); }")
    has_img = await page.evaluate("() => { return !!document.querySelector('img'); }")

    timestamp = time.time()
    
    
    js_report = report_to_js(report['violations'])

    await page.evaluate(f"{js_report}")

    photo = await page.screenshot(full_page=True)

    await page.close()
    # Process the report as needed
    return {
        'url': website,
        'base_url': base_url,
        'report': report,
        'links': links,
        'videos': videos,
        'imgs': imgs,
        'tabable': tabable,
        'has_video': has_video,
        'has_img': has_img,
        'timestamp': timestamp,
        'photo': photo
    }
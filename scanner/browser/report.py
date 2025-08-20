
from typing import List, TypedDict
from urllib.parse import urlparse
from accessibility.ace import AxeReport, get_accessibility_report
from browser.parse import get_base_url, get_imgs, get_links, get_videos
from playwright.async_api import Browser
import time 
from browser.tabbable import is_page_tabbable

class AccessibilityReport(TypedDict, total=False):
    url: str
    base_url: str
    report: AxeReport
    links: List[str]
    videos: List[str]
    imgs: List[str]
    tabable: bool
    timestamp: float


async def generate_report(browser: Browser, website: str = "https://cs.rutgers.edu")-> AccessibilityReport:


    try:
        page = await browser.new_page()
        await page.goto(website)
    except Exception as e:
        return {"error": str(e)}

    base_url = get_base_url(page)
    report = await get_accessibility_report(page)
    # print(report)

    links = await get_links(page)

    videos = await get_videos(page)
    
    imgs = await get_imgs(page)

    tabable = await is_page_tabbable(page)
    has_video = await page.evaluate("() => { return !!document.querySelector('video'); }")
    has_img = await page.evaluate("() => { return !!document.querySelector('img'); }")

    timestamp = time.time()

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
        'timestamp': timestamp
    }
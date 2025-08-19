
from typing import List, TypedDict
from urllib.parse import urlparse
from accessibility.ace import AxeResult, get_accessibility_report
from browser.parse import get_base_url, get_imgs, get_links, get_videos
from playwright.async_api import Browser

from browser.tabbable import is_page_tabbable

class Report(TypedDict, total=False):
    url: str
    base_url: str
    violations: List[AxeResult]
    links: List[str]
    videos: List[str]
    imgs: List[str]
    tabable: bool


async def generate_report(browser: Browser, website: str = "https://cs.rutgers.edu")-> Report:


    try:
        page = await browser.new_page()
        await page.goto(website)
    except Exception as e:
        return {"error": str(e)}

    base_url = get_base_url(page)
    report = await get_accessibility_report(page)
    # print(report)
    violations = report.get('violations', [])
    num_critical_violations = sum(1 for v in violations if v.get('impact') == 'critical')
    num_serious_violations = sum(1 for v in violations if v.get('impact') == 'serious')
    num_moderate_violations = sum(1 for v in violations if v.get('impact') == 'moderate')
    num_minor_violations = sum(1 for v in violations if v.get('impact') == 'minor')
    num_violations = len(violations)

    links = await get_links(page)
    num_of_links = len(links)

    videos = await get_videos(page)
    num_of_videos = len(videos)
    
    imgs = await get_imgs(page)
    num_of_imgs = len(imgs)

    tabable = await is_page_tabbable(page)
    has_video = await page.evaluate("() => { return !!document.querySelector('video'); }")
    has_img = await page.evaluate("() => { return !!document.querySelector('img'); }")
    
    

    await page.close()

    # Process the report as needed
    return {
        'url': website,
        'base_url': base_url,
        'violations': violations,
        'num_violations': num_violations,
        'num_critical_violations': num_critical_violations,
        'num_serious_violations': num_serious_violations,
        'num_moderate_violations': num_moderate_violations,
        'num_minor_violations': num_minor_violations,
        'links': links,
        'num_of_links': num_of_links,
        'videos': videos,
        'num_of_videos': num_of_videos,
        'imgs': imgs,
        'num_of_imgs': num_of_imgs,
        'tabable': tabable,
        'has_video': has_video,
        'has_img': has_img
    }
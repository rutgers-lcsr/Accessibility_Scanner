from typing import List

from scanner.accessibility.ace import get_accessibility_report
from playwright.async_api import Page

from utils.urls import get_full_url, get_netloc, get_website_url


def get_link_js(website):
    return f"""() => {{
        var aTags = Array.from(document.querySelectorAll('a'));
        var links = aTags.filter(a => a.href.startsWith('{website}') || a.href.startsWith('/')).map(a=> a.href).filter(a => !a.includes('#')).filter(a =>!(a == '{website}' ||  a == '{website}/')).filter((value, index, self) => self.indexOf(value) === index);
        
        links = links.map(l => {{
            if (l.startsWith('{website}')) {{
                return l;
            }}
            if (l.startsWith('/')) {{
                return '{website}' + l;
            }}
            return l;
        }}).filter(l => !/(.png|.jpg|.jpeg|.gif|.svg|.zip|.mp4|.webm|.pdf|.doc|.docx|.xls|.xlsx)$/.test(l))
        return links;
}}"""

def get_videos_js():
    return f"""() => {{
        var videoTags = Array.from(document.querySelectorAll('video'));
        var links = videoTags.map(v => {{
            var src = v.src || v.currentSrc;
            return src;
        }}).filter((value, index, self) => self.indexOf(value) === index);
        return links;
}}"""

def get_imgs_js():
    return f"""() => {{
        var imgTags = Array.from(document.querySelectorAll('img'));
        var links = imgTags.map(img => img.src).filter((value, index, self) => self.indexOf(value) === index);
        return links;
}}"""


async def get_links(page:  Page) -> List[str]:
    current_page = get_website_url(page.url)
    links = await page.evaluate(get_link_js(current_page))
    return links

async def get_videos(page: Page) -> List[str]:
    videos = await page.evaluate(get_videos_js())
    return videos

async def get_imgs(page: Page) -> List[str]:
    imgs = await page.evaluate(get_imgs_js())
    return imgs
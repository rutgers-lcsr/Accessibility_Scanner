from typing import List

from scanner.accessibility.ace import get_accessibility_report
from playwright.async_api import Page

from urllib.parse import urlparse

from utils.urls import get_full_url, get_netloc, get_website_url

# Files the crawler inventories instead of auditing as pages (see get_link_js's filter).
DOCUMENT_EXTENSIONS = ('pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx')


def document_type(url: str) -> str | None:
    """The document type of a URL by its path extension, or None."""
    try:
        path = urlparse(url).path
    except ValueError:
        return None
    extension = path.rsplit('.', 1)[-1].lower() if '.' in path.rsplit('/', 1)[-1] else ''
    return extension if extension in DOCUMENT_EXTENSIONS else None


def get_documents_js():
    """JavaScript collecting links to documents on the page (any host, fragment dropped,
    query string kept: a ?download=1 PDF is a different resource)."""
    pattern = '|'.join(DOCUMENT_EXTENSIONS)
    return f"""() => Array.from(document.querySelectorAll('a[href]'))
        .map(a => a.href.split('#')[0])
        .filter(h => /^https?:/i.test(h))
        .filter(h => {{ try {{ return /\\.({pattern})$/i.test(new URL(h).pathname); }} catch (e) {{ return false; }} }})
        .filter((value, index, self) => self.indexOf(value) === index)
    """


def get_link_js(website):
    """JavaScript function to extract links from the page. 
       It filters out links that are not part of the same website and removes duplicates and certain file types.
       
       
       Notes: used to find all the pages on a url.
    """
    
    return f"""() => {{
        var aTags = Array.from(document.querySelectorAll('a'));
        // Drop the fragment rather than the whole link: "/docs#intro" still names a page.
        var links = aTags.filter(a => a.href.startsWith('{website}') || a.href.startsWith('/')).map(a => a.href.split('#')[0]).filter(a =>!(a == '{website}' ||  a == '{website}/')).filter((value, index, self) => self.indexOf(value) === index);
        
        links = links.map(l => {{
            if (!l) return l;
            
            l = l.trim();
            
            // remove parameters from url, This helps to reduce duplicate urls and unnecessary scans
            l = l.split('?')[0];

            if (l.startsWith('{website}')) {{
                return l;
            }}
            if (l.startsWith('/')) {{
                return '{website}' + l;
            }}
            return l;
        }}).filter(l => !/\\.(png|jpg|jpeg|gif|svg|zip|mp4|webm|pdf|doc|docx|xls|xlsx|pptx|ppt|yaml|yml)$/i.test(l))
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

async def get_documents(page: Page) -> List[str]:
    links = await page.evaluate(get_documents_js())
    return [link for link in links if document_type(link)]


async def get_videos(page: Page) -> List[str]:
    videos = await page.evaluate(get_videos_js())
    return videos

async def get_imgs(page: Page) -> List[str]:
    imgs = await page.evaluate(get_imgs_js())
    return imgs
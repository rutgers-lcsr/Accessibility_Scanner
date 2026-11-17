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


def get_link_targets_js():
    """JavaScript collecting every http(s) link on the page (any host, fragment dropped,
    query string kept) with its link text, for the broken-link check."""
    return """() => {
        var seen = {};
        var out = [];
        for (var a of Array.from(document.querySelectorAll('a[href]'))) {
            var href = a.href.split('#')[0];
            if (!/^https?:/i.test(href) || seen[href]) continue;
            seen[href] = true;
            var img = a.querySelector('img[alt]');
            var text = (a.innerText || a.getAttribute('aria-label') || a.getAttribute('title') || (img && img.getAttribute('alt')) || '')
                .replace(/\\s+/g, ' ').trim().slice(0, 300);
            out.push({href: href, text: text});
        }
        return out;
    }"""


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

async def get_link_targets(page: Page) -> List[dict]:
    """``[{'href', 'text'}]`` for every http(s) link on the page."""
    return await page.evaluate(get_link_targets_js())


async def get_documents(page: Page) -> List[str]:
    links = await page.evaluate(get_documents_js())
    return [link for link in links if document_type(link)]


async def get_videos(page: Page) -> List[str]:
    videos = await page.evaluate(get_videos_js())
    return videos

async def get_imgs(page: Page) -> List[str]:
    imgs = await page.evaluate(get_imgs_js())
    return imgs


# Embedded players recognised by their frame's host: (provider, host pattern).
MEDIA_PROVIDERS = (
    ('youtube', r'(^|\.)(youtube\.com|youtube-nocookie\.com|youtu\.be)$'),
    ('vimeo', r'(^|\.)vimeo\.com$'),
    ('kaltura', r'(^|\.)(kaltura\.com|mediaspace\.[\w.-]+)$'),
    ('panopto', r'(^|\.)panopto\.(com|eu)$'),
    ('wistia', r'(^|\.)(wistia\.com|wistia\.net)$'),
    ('brightcove', r'(^|\.)(brightcove\.net|brightcove\.com)$'),
    ('soundcloud', r'(^|\.)soundcloud\.com$'),
    ('spotify', r'(^|\.)spotify\.com$'),
    ('box', r'(^|\.)box\.com$'),
    ('google-drive', r'^drive\.google\.com$'),
)
# Characters of main-content text hashed for stale-content tracking.
MAX_CONTENT_TEXT = 200_000


def get_inventory_js() -> str:
    """JavaScript collecting, for the page it runs on: media (``<video>``, ``<audio>``
    and embedded players) with whether captions are present, resources and form targets
    on other hosts, http:// resources on an https:// page, and the main content's text."""
    providers = ', '.join(f"[{name!r}, new RegExp({pattern!r}, 'i')]" for name, pattern in MEDIA_PROVIDERS)
    return """() => {
        var providers = [%s];
        var abs = function (u) { try { return new URL(u, location.href).href; } catch (e) { return null; } };
        var hostOf = function (u) { try { return new URL(u).host.toLowerCase(); } catch (e) { return ''; } };
        var provider = function (u) {
            var host = hostOf(u);
            for (var p of providers) { if (p[1].test(host)) return p[0]; }
            return null;
        };
        var media = [];
        var index = 0;
        for (var v of Array.from(document.querySelectorAll('video, audio'))) {
            index++;
            var source = v.querySelector('source[src]');
            var src = abs(v.getAttribute('src') || (source && source.getAttribute('src')) || '');
            // A player fed by a script (blob: URL) has no address: name it after the page.
            src = src && /^https?:/i.test(src) ? src.split('#')[0]
                : location.href.split('#')[0] + '#' + v.tagName.toLowerCase() + '-' + index;
            var kinds = Array.from(v.querySelectorAll('track')).map(function (t) { return (t.getAttribute('kind') || 'subtitles').toLowerCase(); });
            var isVideo = v.tagName === 'VIDEO';
            media.push({
                url: src,
                kind: isVideo ? 'video' : 'audio',
                provider: 'html5',
                captions: isVideo ? (kinds.indexOf('captions') >= 0 || kinds.indexOf('subtitles') >= 0 ? 'present' : 'missing') : 'unknown',
                audio_description: kinds.indexOf('descriptions') >= 0
            });
        }
        for (var f of Array.from(document.querySelectorAll('iframe[src], embed[src], object[data]'))) {
            var url = abs(f.getAttribute('src') || f.getAttribute('data'));
            if (!url || !/^https?:/i.test(url)) continue;
            var name = provider(url);
            if (name) media.push({url: url.split('#')[0], kind: 'embed', provider: name, captions: 'unknown', audio_description: false});
        }

        var pageHost = location.host.toLowerCase();
        var thirdParty = [];
        var mixed = [];
        var https = location.protocol === 'https:';
        var collect = function (selector, attr, kind) {
            for (var el of Array.from(document.querySelectorAll(selector))) {
                var u = abs(el.getAttribute(attr));
                if (!u) continue;
                if (https && /^http:/i.test(u)) mixed.push({url: u, tag: el.tagName.toLowerCase()});
                if (!/^https?:/i.test(u)) continue;
                var host = hostOf(u);
                if (host && host !== pageHost) thirdParty.push({url: u, host: host, kind: kind});
            }
        };
        collect('script[src]', 'src', 'script');
        collect('iframe[src]', 'src', 'iframe');
        collect('link[rel~="stylesheet"][href]', 'href', 'stylesheet');
        collect('form[action]', 'action', 'form');
        if (https) {
            for (var el of Array.from(document.querySelectorAll('img[src], video[src], audio[src], source[src], embed[src], object[data]'))) {
                var u = abs(el.getAttribute('src') || el.getAttribute('data'));
                if (u && /^http:/i.test(u)) mixed.push({url: u, tag: el.tagName.toLowerCase()});
            }
        }
        var main = document.querySelector('main, [role="main"]') || document.body;
        var text = main ? (main.innerText || '') : '';
        return {media: media, third_party: thirdParty, mixed_content: mixed.slice(0, 50), text: text.slice(0, %d)};
    }""" % (providers, MAX_CONTENT_TEXT)


async def get_inventory(page: Page) -> dict:
    """``{'media', 'third_party', 'mixed_content', 'text'}`` for the page (get_inventory_js)."""
    return await page.evaluate(get_inventory_js())
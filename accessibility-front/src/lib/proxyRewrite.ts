// Rewrites a proxied page for the report preview (app/proxy/route.tsx).
//
// The page is decoded with its own charset, its URLs are resolved the way a browser
// would (against the final URL after redirects, honouring <base href>), anything that
// would navigate the frame away is dropped, and the report script is injected. It is
// all regex on purpose: apart from these edits the markup must stay exactly as the
// site sent it, and an HTML parser would normalise it.

const URL_ATTRIBUTES = /\b(href|src|poster|data-src)\s*=\s*(["'])([\s\S]*?)\2/gi;
const SRCSET_ATTRIBUTES = /\b(srcset|imagesrcset|data-srcset)\s*=\s*(["'])([\s\S]*?)\2/gi;
const CSS_URLS = /url\(\s*(["']?)([^"')\s]+)\1\s*\)/gi;
const SCRIPT_ELEMENTS = /<script\b[^>]*>([\s\S]*?)<\/script>/gi;
// Assigning the location (not reading it), or calling replace/assign on it, on
// window, document, top, self, parent or bare. `x.location = y` on another object
// does not count, nor does `location.hash = y`, which stays on the page.
const NAVIGATES =
    /(?:^|[^.\w$])(?:(?:window|document|top|self|parent)\s*\.\s*)?location\s*(?:\.\s*href\s*)?=(?!=)|location\s*\.\s*(?:replace|assign)\s*\(/;
const LEAVE_ALONE = /^(?:#|data:|javascript:|mailto:|tel:|blob:|about:)/i;

export function detectCharset(contentType: string, head: string): string {
    const fromHeader = /charset=["']?([\w-]+)/i.exec(contentType)?.[1];
    if (fromHeader) return fromHeader;
    return /<meta\b[^>]*charset=["']?([\w-]+)/i.exec(head)?.[1] ?? 'utf-8';
}

/** The page as text, decoded with the charset from its headers or its <meta>. */
export function decodeBody(bytes: Uint8Array, contentType: string): string {
    const head = new TextDecoder('latin1').decode(bytes.subarray(0, 4096));
    const charset = detectCharset(contentType, head);
    try {
        return new TextDecoder(charset).decode(bytes);
    } catch {
        return new TextDecoder('utf-8').decode(bytes);
    }
}

export function isHtml(contentType: string, body: string): boolean {
    if (/text\/html|application\/xhtml/i.test(contentType)) return true;
    return !contentType.includes('/') && /<(?:!doctype\s+html|html|body)\b/i.test(body);
}

/** A non-HTML text response, shown as is. */
export function textPage(text: string): string {
    const escaped = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    return `<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>Accessibility Report</title></head><body><pre>${escaped}</pre></body></html>`;
}

/** `link` as the browser would resolve it on a page at `base`; unchanged if it cannot be. */
export function resolveUrl(link: string, base: string): string {
    const trimmed = link.trim();
    if (!trimmed || LEAVE_ALONE.test(trimmed)) return link;
    try {
        return new URL(trimmed, base).href;
    } catch {
        return link;
    }
}

/** The URL relative links resolve against: the page's <base href>, else the page URL. */
export function pageBase(html: string, pageUrl: string): string {
    const href = /<base\b[^>]*\bhref\s*=\s*["']?([^"'\s>]+)/i.exec(html)?.[1];
    if (!href) return pageUrl;
    try {
        return new URL(href, pageUrl).href;
    } catch {
        return pageUrl;
    }
}

/** Same-origin path for a site asset, see app/proxy/asset/[...path]/route.ts. */
export function assetProxyUrl(absUrl: string): string {
    const url = new URL(absUrl);
    return `/proxy/asset/${url.protocol.replace(':', '')}/${url.host}${url.pathname}${url.search}`;
}

function rewriteSrcset(value: string, base: string): string {
    return value
        .split(',')
        .map((candidate) => {
            const [url, ...descriptor] = candidate.trim().split(/\s+/);
            return url ? [resolveUrl(url, base), ...descriptor].join(' ') : candidate;
        })
        .join(', ');
}

/** The proxied page, ready to serve. `scriptSrc` is the report script's URL. */
export function rewritePage(html: string, pageUrl: string, scriptSrc: string): string {
    const base = pageBase(html, pageUrl);

    html = html
        .replace(/<base\b[^>]*>/gi, '')
        .replace(SCRIPT_ELEMENTS, (tag, body: string) =>
            NAVIGATES.test(body) ? '<!-- Removed redirect script -->' : tag
        )
        .replace(/<meta\b[^>]*http-equiv\s*=\s*["']?refresh["']?[^>]*>/gi, '')
        .replace(/<meta\b[^>]*http-equiv\s*=\s*["']?content-security-policy["']?[^>]*>/gi, '')
        // The page is re-served as UTF-8 whatever it was; its own declaration would lie.
        .replace(/<meta\b[^>]*\bcharset\s*=[^>]*>/gi, '')
        .replace(/<link\b[^>]*rel\s*=\s*["']?(?:shortcut )?icon["']?[^>]*>/gi, '');

    html = html
        .replace(URL_ATTRIBUTES, (_, attr: string, quote: string, value: string) => {
            return `${attr}=${quote}${resolveUrl(value, base)}${quote}`;
        })
        .replace(SRCSET_ATTRIBUTES, (_, attr: string, quote: string, value: string) => {
            return `${attr}=${quote}${rewriteSrcset(value, base)}${quote}`;
        })
        .replace(CSS_URLS, (_, quote: string, value: string) => {
            return `url(${quote}${resolveUrl(value, base)}${quote})`;
        });

    // Module scripts are fetched in CORS mode, so cross-origin ones fail unless the
    // site sends CORS headers (React/Vite builds). Serve them from our own origin.
    html = html
        .replace(/<script\b[^>]*\btype\s*=\s*["']module["'][^>]*>/gi, (tag) =>
            tag.replace(
                /\bsrc=(["'])(https?:\/\/[^"']+)\1/i,
                (_, q, src) => `src=${q}${assetProxyUrl(src)}${q}`
            )
        )
        .replace(/<link\b[^>]*\brel\s*=\s*["']modulepreload["'][^>]*>/gi, (tag) =>
            tag.replace(
                /\bhref=(["'])(https?:\/\/[^"']+)\1/i,
                (_, q, href) => `href=${q}${assetProxyUrl(href)}${q}`
            )
        );

    // crossorigin forces CORS on stylesheets and scripts, and integrity needs CORS to
    // verify; without them they load in no-cors mode from the site.
    html = html.replace(/<(?:script|link)\b[^>]*>/gi, (tag) =>
        tag.replace(/\s(?:crossorigin|integrity)(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+))?/gi, '')
    );

    const inject = `<meta charset="utf-8"><script defer src="${scriptSrc}"></script>`;
    if (/<head\b[^>]*>/i.test(html)) {
        return html.replace(/<head\b[^>]*>/i, (tag) => `${tag}${inject}`);
    }
    if (/<html\b[^>]*>/i.test(html)) {
        return html.replace(/<html\b[^>]*>/i, (tag) => `${tag}<head>${inject}</head>`);
    }
    return `<head>${inject}</head>${html}`;
}

// Which proxied site a stray same-origin request belongs to (see middleware.ts).
//
// Proxied pages load assets with absolute paths (e.g. a React bundle preloading
// /assets/chunk.css) that resolve against our origin instead of the proxied site.
// The Referer recovers the site: the preview page (/proxy?url=...), a proxied asset
// (/proxy/asset/<scheme>/<host>/...), or a preview page that moved to its own path
// (previewGuard in proxyRewrite.ts), recognised with the preview cookie.

export const APP_PATHS = [
    '/help',
    '/dashboard',
    '/scan',
    '/rules',
    '/proxy',
    '/settings',
    '/domains',
    '/reports',
    '/websites',
    '/owners',
    '/login',
];

export function isAppPath(pathname: string): boolean {
    return (
        pathname === '/' || APP_PATHS.some((p) => pathname === p || pathname.startsWith(`${p}/`))
    );
}

/**
 * The site `pathname` should be fetched from, or null when the request is our own.
 * `previewCookie` is the URL of the page last previewed, if any; `appBaseUrl` is ours.
 */
export function proxiedAssetTarget(
    pathname: string,
    referer: string | null,
    previewCookie: string | undefined,
    appBaseUrl: string
): URL | null {
    if (isAppPath(pathname) || !referer) {
        return null;
    }
    try {
        const refererUrl = new URL(referer);
        if (refererUrl.origin !== new URL(appBaseUrl).origin) {
            return null;
        }
        if (refererUrl.pathname === '/proxy') {
            return new URL(refererUrl.searchParams.get('url') || '');
        }
        const match = refererUrl.pathname.match(/^\/proxy\/asset\/(https?)\/([^/]+)\//);
        if (match) {
            return new URL(`${match[1]}://${match[2]}`);
        }
        if (!previewCookie) {
            return null;
        }
        // Our own pages never sit outside the app paths; a preview can, and it can also
        // sit on one when that is the previewed page's own path.
        const preview = new URL(previewCookie);
        const samePage =
            refererUrl.pathname + refererUrl.search === preview.pathname + preview.search;
        return samePage || !isAppPath(refererUrl.pathname) ? preview : null;
    } catch {
        return null;
    }
}

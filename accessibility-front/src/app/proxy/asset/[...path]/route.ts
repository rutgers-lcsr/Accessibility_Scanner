import { fetchPublicUrl, UnsafeTargetError } from '@/lib/safeTarget';
import { NextRequest, NextResponse } from 'next/server';

const MAX_ASSET_BYTES = 25 * 1024 * 1024;

// Serves proxied site assets from our own origin as /proxy/asset/<scheme>/<host>/<path>.
// Module scripts are always fetched in CORS mode, so they must come from the same
// origin as the proxied page; relative imports between JS chunks also resolve back
// to this route because the original URL path structure is preserved.
export async function GET(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
    const { path } = await ctx.params;
    const [scheme, host, ...rest] = path;

    if ((scheme !== 'http' && scheme !== 'https') || !host) {
        return new NextResponse('Invalid asset URL', { status: 400 });
    }

    // A site's `navigator.serviceWorker.register('/sw.js')` would resolve to this origin
    // and, if served, install its worker on the whole app. Browsers mark that fetch.
    if (req.headers.get('service-worker')) {
        return new NextResponse('Service workers are not proxied', { status: 403 });
    }

    const url = `${scheme}://${host}/${rest.join('/')}${req.nextUrl.search}`;

    try {
        // Only public hosts, with certificate verification on (see lib/safeTarget).
        const response = await fetchPublicUrl(url, {
            headers: {
                'User-Agent': req.headers.get('User-Agent') || 'Mozilla/5.0',
                Accept: req.headers.get('Accept') || '*/*',
            },
            responseType: 'arraybuffer',
            maxContentLength: MAX_ASSET_BYTES,
        });

        return new NextResponse(response.data, {
            status: response.status,
            headers: {
                'Content-Type': String(
                    response.headers['content-type'] || 'application/octet-stream'
                ),
                'Access-Control-Allow-Origin': '*',
                'Cache-Control': 'public, max-age=3600',
            },
        });
    } catch (err) {
        if (err instanceof UnsafeTargetError) {
            return new NextResponse('Forbidden', { status: 403 });
        }
        return new NextResponse('Failed to fetch asset', { status: 502 });
    }
}

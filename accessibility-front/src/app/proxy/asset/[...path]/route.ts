import axios from 'axios';
import https from 'https';
import { NextRequest, NextResponse } from 'next/server';

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

    const url = `${scheme}://${host}/${rest.join('/')}${req.nextUrl.search}`;

    try {
        const agent = new https.Agent({
            rejectUnauthorized: false,
        });
        const response = await axios.get(url, {
            headers: {
                'User-Agent': req.headers.get('User-Agent') || 'Mozilla/5.0',
                Accept: req.headers.get('Accept') || '*/*',
            },
            httpsAgent: agent,
            responseType: 'arraybuffer',
            validateStatus: () => true,
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
    } catch {
        return new NextResponse('Failed to fetch asset', { status: 502 });
    }
}

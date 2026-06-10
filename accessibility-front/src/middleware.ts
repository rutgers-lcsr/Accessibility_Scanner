import { getCurrentUser } from 'next-cas-client/app';
import { NextRequest, NextResponse } from 'next/server';

const baseUrl = process.env.NEXT_PUBLIC_BASE_URL as string;
const casUrl = process.env.NEXT_PUBLIC_CAS_URL as string;

const appPaths = [
    '/help',
    '/rules',
    '/proxy',
    '/settings',
    '/domains',
    '/reports',
    '/websites',
    '/login',
];

// Proxied pages load assets with absolute paths (e.g. a React bundle preloading
// /assets/chunk.css) that resolve against our origin instead of the proxied site.
// Use the Referer to recover the original site and forward to the asset proxy.
function proxiedAssetRewrite(request: NextRequest) {
    const pathname = request.nextUrl.pathname;
    if (pathname === '/' || appPaths.some((p) => pathname === p || pathname.startsWith(`${p}/`))) {
        return null;
    }
    const referer = request.headers.get('referer');
    if (!referer) {
        return null;
    }
    try {
        const refererUrl = new URL(referer);
        if (refererUrl.origin !== new URL(baseUrl).origin) {
            return null;
        }
        let target: URL | null = null;
        if (refererUrl.pathname === '/proxy') {
            target = new URL(refererUrl.searchParams.get('url') || '');
        } else {
            const match = refererUrl.pathname.match(/^\/proxy\/asset\/(https?)\/([^/]+)\//);
            if (match) {
                target = new URL(`${match[1]}://${match[2]}`);
            }
        }
        if (!target) {
            return null;
        }
        return NextResponse.rewrite(
            new URL(
                `/proxy/asset/${target.protocol.replace(':', '')}/${target.host}${pathname}${request.nextUrl.search}`,
                request.url
            )
        );
    } catch {
        return null;
    }
}

export async function middleware(request: NextRequest) {
    const user = await getCurrentUser();
    if (!user) {
        const redirect = `${baseUrl}${request.nextUrl.pathname}`;
        return NextResponse.redirect(
            new URL(
                `${casUrl}/login?service=${encodeURIComponent(`${baseUrl}/api/cas/login?redirect=${redirect}`)}`,
                request.url
            )
        );
    }
    const assetRewrite = proxiedAssetRewrite(request);
    if (assetRewrite) {
        return assetRewrite;
    }
    return NextResponse.next();
}

export const config = {
    matcher: '/((?!api|_next/static|_next/image|favicon.ico|login).*)',
    runtime: 'nodejs',
};

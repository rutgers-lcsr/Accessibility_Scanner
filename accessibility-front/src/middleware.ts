import { getCurrentUser } from 'next-cas-client/app';
import { PREVIEW_COOKIE } from '@/lib/proxyRewrite';
import { proxiedAssetTarget } from '@/lib/proxyTarget';
import { NextRequest, NextResponse } from 'next/server';

const baseUrl = process.env.NEXT_PUBLIC_BASE_URL as string;
const casUrl = process.env.NEXT_PUBLIC_CAS_URL as string;

// Stray same-origin requests from a proxied page go to the asset proxy (lib/proxyTarget).
function proxiedAssetRewrite(request: NextRequest) {
    const target = proxiedAssetTarget(
        request.nextUrl.pathname,
        request.headers.get('referer'),
        request.cookies.get(PREVIEW_COOKIE)?.value,
        baseUrl
    );
    if (!target) {
        return null;
    }
    return NextResponse.rewrite(
        new URL(
            `/proxy/asset/${target.protocol.replace(':', '')}/${target.host}${request.nextUrl.pathname}${request.nextUrl.search}`,
            request.url
        )
    );
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
    matcher: '/((?!api|_next/static|_next/image|favicon.ico|login|health).*)',
    runtime: 'nodejs',
};

import { User } from '@/lib/types/user';
import { CasUser, ValidatorProtocol } from 'next-cas-client';
import { getCurrentUser, handleAuth } from 'next-cas-client/app';
import { NextRequest, NextResponse } from 'next/server';
const API_URL = process.env.API_URL;
const BASE_URL = process.env.NEXT_PUBLIC_BASE_URL || '';

// Backend paths the browser may reach through this proxy. The login endpoint is
// deliberately absent: only loadUser (below) may call it.
const ALLOWED_PATHS = [
    '/api/auth/logout',
    '/api/dashboard',
    '/api/domains',
    '/api/reports',
    '/api/sites',
    '/api/users',
    '/api/websites',
    '/api/scans',
    '/api/axe',
    '/api/settings',
    '/api/v1',
    '/api/docs',
    '/api/apispec_1.json',
    '/api/flasgger_static',
];

// Only these client headers reach the backend. Cookies (the CAS session) and any
// client-supplied identity headers never do; Authorization is set from the session.
// X-Forwarded-Proto is not forwarded: the backend is reached over plain HTTP and must
// build its redirects for that, not for the browser's https.
const FORWARDED_REQUEST_HEADERS = [
    'content-type',
    'accept',
    'accept-language',
    'user-agent',
    'x-api-key',
    'x-forwarded-for',
    // conditional requests, so cached screenshots revalidate instead of re-downloading
    'if-none-match',
    'if-modified-since',
];

// Only these backend headers reach the client. Set-Cookie must not, and the body is
// already decoded here so content-encoding/content-length would be wrong.
const FORWARDED_RESPONSE_HEADERS = [
    'content-type',
    'content-disposition',
    'cache-control',
    'etag',
    'last-modified',
    'retry-after',
    'x-ratelimit-limit',
    'x-ratelimit-remaining',
    'x-ratelimit-reset',
];

function isAllowedPath(path: string) {
    return ALLOWED_PATHS.some((allowed) => path === allowed || path.startsWith(`${allowed}/`));
}

function isSameOriginTarget(target: string) {
    try {
        return new URL(target, BASE_URL).origin === new URL(BASE_URL).origin;
    } catch {
        return false;
    }
}

function rewriteUrl(path: string, query: string) {
    const url = query ? `${API_URL}${path}?${query}` : `${API_URL}${path}`;
    return url;
}

async function proxyRequest(req: NextRequest, method: string) {
    const path = req.nextUrl.pathname;

    if (!isAllowedPath(path)) {
        return new NextResponse('Not Found', { status: 404 });
    }

    const query = req.nextUrl.searchParams.toString();

    const url = rewriteUrl(path, query);
    const user: User | null = await getCurrentUser();

    const headers = new Headers();
    for (const name of FORWARDED_REQUEST_HEADERS) {
        const value = req.headers.get(name);
        if (value) {
            headers.set(name, value);
        }
    }
    if (user) {
        headers.set('Authorization', `Bearer ${user.access_token || ''}`);
    } else {
        // API-key clients may also present their key as a bearer token.
        const authorization = req.headers.get('authorization');
        if (authorization) {
            headers.set('Authorization', authorization);
        }
    }

    const request: RequestInit = {
        method,
        headers,
        body: ['POST', 'PUT', 'PATCH'].includes(method) ? await req.text() : null,
        redirect: 'follow',
    };
    try {
        const res = await fetch(url, request);

        const data = await res.arrayBuffer();

        if (res.status === 401) {
            return new NextResponse('Unauthorized', { status: 401 });
        }

        const responseHeaders = new Headers();
        for (const name of FORWARDED_RESPONSE_HEADERS) {
            const value = res.headers.get(name);
            if (value) {
                responseHeaders.set(name, value);
            }
        }

        return new NextResponse(data, {
            status: res.status,
            headers: responseHeaders,
        });
    } catch (error) {
        // Reaching here means no HTTP response came back from the backend at all
        // (DNS, connection, TLS, ...). Say so in the server log, not just a bare 500.
        const cause = error instanceof Error ? (error.cause ?? error.message) : error;
        console.error(`API proxy: ${method} ${url} failed:`, cause);
        return new NextResponse('Internal Server Error', { status: 500 });
    }
}

async function loadUser(casUser: CasUser) {
    const api_user = await fetch(`${API_URL}/api/auth/cas`, {
        method: 'GET',
        headers: {
            'x-cas-user': casUser.user,
            'x-cas-server': process.env.NEXT_PUBLIC_CAS_URL || '',
            // Proves to the backend that this request comes from the proxy, which has
            // already validated the CAS ticket. Must match the backend's value.
            'X-Internal-Secret': process.env.INTERNAL_AUTH_SECRET || '',
        },
    });

    return { ...casUser, ...(await api_user.json()) };
}

const cas_get_route = handleAuth({ loadUser, validator: ValidatorProtocol.CAS30 });

export async function GET(req: NextRequest) {
    if (req.nextUrl.pathname === '/api/cas/login') {
        // The CAS client redirects to ?redirect= after login; keep it on this origin.
        const redirect = req.nextUrl.searchParams.get('redirect');
        if (redirect && !isSameOriginTarget(redirect)) {
            return new NextResponse('Invalid redirect', { status: 400 });
        }
        return cas_get_route(req, {
            params: { client: 'login' },
        });
    }
    if (req.nextUrl.pathname === '/api/cas/logout') {
        return cas_get_route(req, {
            params: { client: 'logout' },
        });
    }
    return proxyRequest(req, 'GET');
}
export async function POST(req: NextRequest) {
    return proxyRequest(req, 'POST');
}
export async function PUT(req: NextRequest) {
    return proxyRequest(req, 'PUT');
}
export async function PATCH(req: NextRequest) {
    return proxyRequest(req, 'PATCH');
}
export async function DELETE(req: NextRequest) {
    return proxyRequest(req, 'DELETE');
}

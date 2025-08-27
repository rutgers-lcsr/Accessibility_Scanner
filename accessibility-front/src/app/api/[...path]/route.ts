import { NextRequest, NextResponse } from 'next/server';

const API_URL = process.env.API_URL;

function rewriteUrl(path: string[], query: string) {
    return `${API_URL}/api/${path.join('/')}?${query}`;
}

async function proxyRequest(req: NextRequest, ctx: RouteContext<'/api/[...path]'>, method: string) {
    const path = (await ctx.params).path;
    const query = req.nextUrl.searchParams.toString();
    const url = rewriteUrl(path, query);

    const init: RequestInit = {
        method,
        headers: req.headers,
    };

    // Only set body for methods that support it
    if (['POST', 'PUT', 'PATCH'].includes(method)) {
        init.body = await req.text();
    }

    const res = await fetch(url, init);
    const data = await res.arrayBuffer();

    return new NextResponse(data, {
        status: res.status,
        headers: res.headers,
    });
}

export async function GET(req: NextRequest, ctx: RouteContext<'/api/[...path]'>) {
    return proxyRequest(req, ctx, 'GET');
}
export async function POST(req: NextRequest, ctx: RouteContext<'/api/[...path]'>) {
    return proxyRequest(req, ctx, 'POST');
}
export async function PUT(req: NextRequest, ctx: RouteContext<'/api/[...path]'>) {
    return proxyRequest(req, ctx, 'PUT');
}
export async function PATCH(req: NextRequest, ctx: RouteContext<'/api/[...path]'>) {
    return proxyRequest(req, ctx, 'PATCH');
}
export async function DELETE(req: NextRequest, ctx: RouteContext<'/api/[...path]'>) {
    return proxyRequest(req, ctx, 'DELETE');
}

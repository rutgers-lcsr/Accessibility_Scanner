import { User } from '@/lib/types/user';
import { CasUser, ValidatorProtocol } from 'next-cas-client';
import { getCurrentUser, handleAuth } from 'next-cas-client/app';
import { NextRequest, NextResponse } from 'next/server';
const API_URL = process.env.API_URL;

function rewriteUrl(path: string, query: string) {
    return `${API_URL}${path}/?${query}`;
}

async function proxyRequest(req: NextRequest, method: string) {
    const path = req.nextUrl.pathname;
    
    const query = req.nextUrl.searchParams.toString();
    
    const url = rewriteUrl(path, query);
    const user: User | null = await getCurrentUser();

    if(user){
        if (req.nextUrl.pathname === '/api/auth/refresh'){
            req.headers.set('Authorization', `Bearer ${user?.refresh_token || ''}`)
        }else  {
            req.headers.set('Authorization', `Bearer ${user?.access_token || ''}`)
        }
    }
    


    const request:RequestInit = {
        method,
        headers: req.headers,
        body: ['POST', 'PUT', 'PATCH'].includes(method) ? await req.text() : null,
        redirect: 'follow'
    };
    try {

        const res = await fetch(url, request);

        const data = await res.arrayBuffer();


        if(res.status === 401){
            return new NextResponse('Unauthorized', { status: 401 });
        }

        return new NextResponse(data, {
            status: res.status,
            headers: res.headers,
        });
    }catch (error) {
        return new NextResponse('Internal Server Error', { status: 500 });
    }
}

async function loadUser(casUser: CasUser) {
    const api_user = await fetch(`${API_URL}/api/auth/cas`, {
        method: 'GET',
        headers: {
            'x-cas-user': casUser.user,
            'x-cas-server': process.env.NEXT_PUBLIC_CAS_URL || '',
        }
    });

    return {...casUser,...await api_user.json() }
}


const cas_get_route = handleAuth({ loadUser, validator: ValidatorProtocol.CAS30 });

export async function GET(req: NextRequest) {

    if (req.nextUrl.pathname === '/api/cas/login') {
        // Handle token refresh
        return cas_get_route(req, {params: {client: 'login'}});
    }
    if (req.nextUrl.pathname === '/api/cas/logout'){
        return cas_get_route(req, {params: {client: 'logout'}});
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

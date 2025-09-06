import { getCurrentUser } from 'next-cas-client/app';
import { NextRequest, NextResponse } from 'next/server';


const baseUrl = process.env.NEXT_PUBLIC_BASE_URL as string;
const casUrl = process.env.NEXT_PUBLIC_CAS_URL as string;

export async function middleware(request: NextRequest) {
    const user = await getCurrentUser();
    if (!user && process.env.NODE_ENV === 'production') {
        return NextResponse.redirect(new URL(`${casUrl}/login?service=${encodeURIComponent(`${baseUrl}/api/cas/login`)}`, request.url))
    }
    return NextResponse.next();
}
 
export const config = {
  matcher: '/((?!api|_next/static|_next/image|favicon.ico|login).*)',
  runtime: 'nodejs',
}
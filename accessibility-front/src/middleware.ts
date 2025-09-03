import { getCurrentUser } from 'next-cas-client/app';
import { NextRequest, NextResponse } from 'next/server';

 
export async function middleware(request: NextRequest) {
    const user = await getCurrentUser();
    console.log("from middleware", request.url)
    if (!user && process.env.NODE_ENV === 'production') {
        return NextResponse.redirect(new URL('/login', request.url))
    }
    return NextResponse.next();
}
 
export const config = {
  matcher: '/((?!api|_next/static|_next/image|favicon.ico|login).*)',
  runtime: 'nodejs',
}
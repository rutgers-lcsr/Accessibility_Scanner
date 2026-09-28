import { devAuthUser, loadUser } from '@/lib/loadUser';
import { getIronSession } from 'iron-session';
import { cookies } from 'next/headers';
import { NextRequest, NextResponse } from 'next/server';

// Local development without a CAS server. Writes the same session next-cas-client's
// login handler would (its SessionOptions, which it does not export), with the user
// from DEV_AUTH_USER in place of a validated CAS ticket. A 404 in production builds
// or when DEV_AUTH_USER is unset, so it cannot be reached by accident.
export async function GET(req: NextRequest) {
    const user = devAuthUser();
    if (!user) {
        return new NextResponse('Not Found', { status: 404 });
    }
    const session = await getIronSession<{ user?: unknown }>(await cookies(), {
        cookieName: 'SESSIONID',
        password: process.env.NEXT_CAS_CLIENT_SECRET as string,
        ttl: 86400,
        cookieOptions: { secure: false },
    });
    session.user = await loadUser({ user, attributes: {} });
    await session.save();

    // Only same-origin targets, like /api/cas/login.
    const redirect = req.nextUrl.searchParams.get('redirect') || '/';
    const target = new URL(redirect, req.nextUrl.origin);
    return NextResponse.redirect(target.origin === req.nextUrl.origin ? target : new URL('/', req.nextUrl.origin));
}

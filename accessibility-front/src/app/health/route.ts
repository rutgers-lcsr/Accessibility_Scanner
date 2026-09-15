import { NextResponse } from 'next/server';

// Container health check target. Excluded from the auth middleware so it answers
// without a session instead of redirecting to CAS.
export function GET() {
    return NextResponse.json({ status: 'ok' });
}

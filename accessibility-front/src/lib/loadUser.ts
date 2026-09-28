import { CasUser } from 'next-cas-client';

const API_URL = process.env.API_URL;

// Turns a validated CAS identity into the session user: the backend creates the
// account if needed and returns its profile with the API token.
export async function loadUser(casUser: CasUser) {
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

// The NetID to sign in as without a CAS server (start_dev.sh sets it unless run with
// --cas). Never honoured in a production build.
export function devAuthUser(): string | null {
    if (process.env.NODE_ENV === 'production') return null;
    return process.env.DEV_AUTH_USER || null;
}

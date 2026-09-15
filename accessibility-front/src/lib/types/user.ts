import { CasUser } from 'next-cas-client';
export type User = CasUser & {
    id: string;
    email: string;
    is_admin: boolean;
    is_active: boolean;
    access_token: string;
    username: string;
};

/**
 * The part of the session that may be passed to client components. Props given to a
 * client component are serialised into the page, so the backend token must never be
 * on this type; the API proxy attaches it server-side from the session instead.
 */
export type PublicUser = Pick<User, 'id' | 'email' | 'username' | 'user' | 'is_admin' | 'is_active'>;

export function toPublicUser(user: User | null): PublicUser | null {
    if (!user) return null;
    return {
        id: user.id,
        email: user.email,
        username: user.username,
        user: user.user,
        is_admin: user.is_admin,
        is_active: user.is_active,
    };
}

export type ApiKey = {
    id: number;
    name: string;
    prefix: string;
    last_used_at: string | null;
    created_at: string | null;
};

// Returned only once, on creation
export type CreatedApiKey = ApiKey & {
    key: string;
};

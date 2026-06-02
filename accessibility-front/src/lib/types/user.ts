import { CasUser } from 'next-cas-client';
export type User = CasUser & {
    id: string;
    email: string;
    is_admin: boolean;
    is_active: boolean;
    access_token: string;
    refresh_token: string;
    username: string;
};

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

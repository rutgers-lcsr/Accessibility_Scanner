import { CasUser } from "next-cas-client";
export type User = CasUser &{
    id: string;
    email: string;
    is_admin: boolean;
    is_active: boolean;
    access_token: string;
    refresh_token: string;
};

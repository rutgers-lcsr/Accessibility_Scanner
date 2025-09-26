import { User } from '@/lib/types/user';
import { WebsitesProvider } from '@/providers/Websites';
import { getCurrentUser } from 'next-cas-client/app';
import { ReactNode } from 'react';

export default async function Layout({ children }: { children: ReactNode }) {
    const user = await getCurrentUser<User>(); // Assume this function fetches the current user

    return <WebsitesProvider user={user}>{children}</WebsitesProvider>;
}

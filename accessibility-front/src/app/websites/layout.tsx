import { User, toPublicUser } from '@/lib/types/user';
import { WebsitesProvider } from '@/providers/Websites';
import { getCurrentUser } from 'next-cas-client/app';
import { ReactNode } from 'react';

export default async function Layout({ children }: { children: ReactNode }) {
    const user = toPublicUser(await getCurrentUser<User>());

    return <WebsitesProvider user={user}>{children}</WebsitesProvider>;
}

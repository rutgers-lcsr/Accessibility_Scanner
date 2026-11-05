import { User, toPublicUser } from '@/lib/types/user';
import { ReportsProvider } from '@/providers/Reports';
import { getCurrentUser } from 'next-cas-client/app';
import { ReactNode } from 'react';

export default async function Layout({ children }: { children: ReactNode }) {
    const user = toPublicUser(await getCurrentUser<User>());

    return (
        <>
            {/* No heading here: the list and each report render their own h1. */}
            <ReportsProvider user={user}>{children}</ReportsProvider>
        </>
    );
}

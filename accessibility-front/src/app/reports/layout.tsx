import PageHeading from '@/components/PageHeading';
import { User } from '@/lib/types/user';
import { ReportsProvider } from '@/providers/Reports';
import { getCurrentUser } from 'next-cas-client/app';
import { ReactNode } from 'react';

export default async function Layout({ children }: { children: ReactNode }) {
    const user = await getCurrentUser<User>();

    return (
        <>
            <ReportsProvider user={user}>
                <PageHeading
                    title="Accessibility Reports"
                    subtitle="Individual accessibility reports."
                />
                {children}
            </ReportsProvider>
        </>
    );
}

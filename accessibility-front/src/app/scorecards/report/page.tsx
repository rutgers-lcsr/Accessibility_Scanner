import PageError from '@/components/PageError';
import PageLoading from '@/components/PageLoading';
import { User } from '@/lib/types/user';
import { getCurrentUser } from 'next-cas-client/app';
import { Suspense } from 'react';
import type { Metadata } from 'next';
import ComplianceReport from './ComplianceReport';

export const metadata: Metadata = { title: 'Compliance report' };

export default async function Page() {
    const user = await getCurrentUser<User>();
    if (!user) {
        return (
            <PageError
                status={403}
                title="Access Denied"
                subTitle="You must be logged in to view this page."
            />
        );
    }
    // The report reads ?department= with useSearchParams.
    return (
        <Suspense fallback={<PageLoading />}>
            <ComplianceReport />
        </Suspense>
    );
}

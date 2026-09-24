'use client';
import PageError from '@/components/PageError';
import PageLoading from '@/components/PageLoading';
import { useBulkFindingStatus } from '@/hooks/useBulkFindingStatus';
import { fetcherApi } from '@/lib/api';
import { platformHint } from '@/lib/guides';
import { WebsiteFixFirst } from '@/lib/types/finding';
import { PublicUser } from '@/lib/types/user';
import { useUrlFilters } from '@/lib/urlFilters';
import { useUser } from '@/providers/User';
import useSWR from 'swr';
import FixFirstList from './FixFirstList';

type Props = {
    websiteId: number;
    user: PublicUser | null;
    canEdit: boolean;
    categories: string[];
    // Refresh the website (header counts) after a verdict changed what counts.
    onCountsChanged?: () => void;
};

function FixFirst({ websiteId, user, canEdit, categories, onCountsChanged }: Props) {
    const { handlerUserApiRequest } = useUser();
    const { params } = useUrlFilters();
    const { data, error, isLoading, mutate } = useSWR<WebsiteFixFirst>(
        `/api/websites/${websiteId}/fix-first`,
        user ? handlerUserApiRequest<WebsiteFixFirst> : fetcherApi<WebsiteFixFirst>
    );
    const onBulkStatus = useBulkFindingStatus(websiteId, async () => {
        await mutate();
        onCountsChanged?.();
    });

    if (error) return <PageError status={500} title="Error loading the fix list" />;
    if (isLoading || !data) return <PageLoading />;

    return (
        <div className="mt-2">
            <FixFirstList
                websiteId={websiteId}
                data={data}
                canEdit={canEdit}
                platform={platformHint(categories)}
                onBulkStatus={onBulkStatus}
                focusRule={params.get('rule')}
            />
        </div>
    );
}

export default FixFirst;

'use client';

import PageError from '@/components/PageError';
import PageLoading from '@/components/PageLoading';
import { fetcherApi } from '@/lib/api';
import { HistoryPoint } from '@/lib/types/history';
import { Paged } from '@/lib/types/Paged';
import { User } from '@/lib/types/user';
import { useUser } from '@/providers/User';
import useSWR from 'swr';
import HistoryChart from './HistoryChart';

type Props = {
    siteId: number;
    user: User | null;
};

function SiteHistoryChart({ siteId, user }: Props) {
    const { handlerUserApiRequest } = useUser();

    // This component is only mounted when its row is expanded, so the request
    // fires lazily — collapsed rows make no history calls.
    const { data, error, isLoading } = useSWR(
        `/api/sites/${siteId}/history`,
        user ? handlerUserApiRequest<Paged<HistoryPoint>> : fetcherApi<Paged<HistoryPoint>>
    );

    if (error) return <PageError status={500} title="Error loading URL history" />;
    if (isLoading || !data) return <PageLoading minimal />;

    return <HistoryChart data={data.items} x="timestamp" compact />;
}

export default SiteHistoryChart;

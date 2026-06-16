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
    websiteId: number;
    user: User | null;
};

function WebsiteHistoryChart({ websiteId, user }: Props) {
    const { handlerUserApiRequest } = useUser();

    const { data, error, isLoading } = useSWR(
        `/api/websites/${websiteId}/history`,
        user ? handlerUserApiRequest<Paged<HistoryPoint>> : fetcherApi<Paged<HistoryPoint>>
    );

    if (error) return <PageError status={500} title="Error loading website history" />;
    if (isLoading || !data) return <PageLoading minimal />;

    return <HistoryChart data={data.items} x="date" />;
}

export default WebsiteHistoryChart;

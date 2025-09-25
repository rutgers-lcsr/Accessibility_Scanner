'use client';
import { APIError, fetcherApi } from '@/lib/api';
import { getInitalPageSize, PageSize } from '@/lib/browser';
import { Paged } from '@/lib/types/Paged';
import { User } from '@/lib/types/user';
import { Website } from '@/lib/types/website';
import { useRouter } from 'next/navigation';
import React, { createContext, useContext, useState } from 'react';
import useSWR from 'swr';
import { useAlerts } from './Alerts';
import { useUser } from './User';

type WebsitesContextType = {
    websites: Website[] | null;
    websitesTotal: number;
    error: APIError | null;
    isLoading: boolean;
    WebsitePage: number;
    WebsiteLimit: number;
    requestWebsite: (url: string) => Promise<Website | null>;
    setWebsiteSearch: (query: string) => void;
    setWebsitePage: (page: number) => void;
    setWebsiteLimit: (limit: PageSize) => void;
    openWebsite: (id: number) => void;
};

const WebsitesContext = createContext<WebsitesContextType | undefined>(undefined);

export const WebsitesProvider: React.FC<{ children: React.ReactNode; user: User | null }> = ({
    children,
    user,
}) => {
    const router = useRouter();
    const [page, setPage] = useState(1);

    const [limit, setLimit] = useState(getInitalPageSize);

    const [searchUrl, setSearchUrl] = useState('');
    const { handlerUserApiRequest } = useUser();

    const { addAlert } = useAlerts();
    const { data, error, isLoading, mutate } = useSWR(
        `/api/websites/?page=${page}&limit=${limit}${searchUrl ? `&search=${searchUrl}` : ''}`,
        user ? handlerUserApiRequest<Paged<Website>> : fetcherApi<Paged<Website>>
    );

    const openWebsite = (id: number) => {
        // Logic to open the website
        router.push(`/websites?id=${id}`);
    };

    const requestWebsite = async (url: string) => {
        try {
            const getter = user ? handlerUserApiRequest<Website> : fetcherApi<Website>;

            const data = await getter(`/api/websites/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ base_url: url }),
            });
            addAlert('Website created successfully', 'success');
            mutate();
            return data;
        } catch (error) {
            addAlert(`Failed to add website ${(error as APIError).getReason()}`, 'error');
            return null;
        }
    };

    return (
        <WebsitesContext.Provider
            value={{
                websites: data?.items ?? null,
                websitesTotal: data?.count ?? 0,
                error,
                isLoading,
                openWebsite,
                WebsitePage: page,
                WebsiteLimit: limit,
                setWebsitePage: setPage,
                setWebsiteLimit: setLimit,
                setWebsiteSearch: setSearchUrl,
                requestWebsite,
            }}
        >
            {children}
        </WebsitesContext.Provider>
    );
};

export const useWebsites = () => {
    const context = useContext(WebsitesContext);
    if (!context) {
        throw new Error('useWebsites must be used within a WebsitesProvider');
    }
    return context;
};

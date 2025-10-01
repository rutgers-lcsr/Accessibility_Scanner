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
    categories?: string[];
    requestWebsite: (url: string) => Promise<Website | null>;
    setWebsiteSearch: (query: string) => void;
    setWebsitePage: (page: number) => void;
    setWebsiteLimit: (limit: PageSize) => void;
    setWebsiteCategories: (categories: string[]) => void;
    setWebsiteOrderBy: (orderBy: 'url' | 'violations' | 'last_scanned') => void;
    openWebsite: (id: number) => void;
    exportCSV: () => void;
};

const WebsitesContext = createContext<WebsitesContextType | undefined>(undefined);

export const WebsitesProvider: React.FC<{ children: React.ReactNode; user: User | null }> = ({
    children,
    user,
}) => {
    const router = useRouter();

    // website query options
    const [page, setPage] = useState(1);
    const [limit, setLimit] = useState(getInitalPageSize);
    const [searchUrl, setSearchUrl] = useState('');
    const [searchCategories, setSearchCategories] = useState<string[]>([]);
    const [orderBy, setOrderBy] = useState<'url' | 'violations' | 'last_scanned'>('url');

    const { handlerUserApiRequest } = useUser();

    const { addAlert } = useAlerts();
    const { data, error, isLoading, mutate } = useSWR(
        `/api/websites/?page=${page}&limit=${limit}${searchUrl ? `&search=${searchUrl}` : ''}${searchCategories.length ? `&category=${searchCategories.join(',')}` : ''}&orderBy=${orderBy}`,
        user ? handlerUserApiRequest<Paged<Website>> : fetcherApi<Paged<Website>>
    );
    const { data: categories } = useSWR(
        `/api/websites/categories`,
        user ? handlerUserApiRequest<string[]> : fetcherApi<string[]>
    );

    const exportCSV = () => {
        const url = `/api/websites/?page=${page}&limit=${limit}${searchUrl ? `&search=${searchUrl}` : ''}${searchCategories.length ? `&category=${searchCategories.join(',')}` : ''}&orderBy=${orderBy}&format=csv`;
        window.open(url, '_blank');
    };

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
                categories: categories,
                WebsitePage: page,
                WebsiteLimit: limit,
                setWebsitePage: setPage,
                setWebsiteLimit: setLimit,
                setWebsiteSearch: setSearchUrl,
                setWebsiteCategories: setSearchCategories,
                setWebsiteOrderBy: setOrderBy,
                requestWebsite,
                exportCSV,
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

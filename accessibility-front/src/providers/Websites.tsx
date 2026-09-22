'use client';
import { APIError, fetcherApi } from '@/lib/api';
import { getInitalPageSize, PageSize, savePageSize } from '@/lib/browser';
import { pageParam, useUrlFilters } from '@/lib/urlFilters';
import { Paged } from '@/lib/types/Paged';
import { PublicUser } from '@/lib/types/user';
import { Website } from '@/lib/types/website';
import { useRouter } from 'next/navigation';
import React, { createContext, useContext, useState } from 'react';
import useSWR from 'swr';
import { useAlerts } from './Alerts';
import { useUser } from './User';

// Extra fields a site admin can send when adding a website (see POST /api/websites/).
export type NewWebsiteOptions = {
    admin?: string;
    categories?: string[];
    create_domain?: boolean;
};

type WebsitesContextType = {
    websites: Website[] | null;
    websitesTotal: number;
    error: APIError | null;
    isLoading: boolean;
    WebsitePage: number;
    WebsiteLimit: number;
    WebsiteSearch: string;
    WebsiteCategories: string[];
    WebsiteOrderBy: WebsiteOrder;
    categories?: string[];
    requestWebsite: (url: string, options?: NewWebsiteOptions) => Promise<Website | null>;
    setWebsiteSearch: (query: string) => void;
    setWebsitePage: (page: number) => void;
    setWebsiteLimit: (limit: PageSize) => void;
    setWebsiteCategories: (categories: string[]) => void;
    setWebsiteOrderBy: (orderBy: WebsiteOrder) => void;
    openWebsite: (id: number) => void;
    exportCSV: () => void;
};

export type WebsiteOrder = 'url' | 'violations' | 'last_scanned';

const WebsitesContext = createContext<WebsitesContextType | undefined>(undefined);

export const WebsitesProvider: React.FC<{ children: React.ReactNode; user: PublicUser | null }> = ({
    children,
    user,
}) => {
    const router = useRouter();

    // Website query options. Search, categories, order and page live in the URL (see
    // useUrlFilters) so they are still there after opening a website and coming back;
    // the page size is a per-browser preference kept in localStorage.
    const { params, setFilters } = useUrlFilters();
    const page = pageParam(params.get('page'));
    const searchUrl = params.get('search') ?? '';
    const searchCategories = params.get('category')?.split(',').filter(Boolean) ?? [];
    const orderParam = params.get('orderBy');
    const orderBy: WebsiteOrder =
        orderParam === 'violations' || orderParam === 'last_scanned' ? orderParam : 'url';
    const [limit, setLimitState] = useState(getInitalPageSize);

    const setPage = (next: number) => setFilters({ page: next > 1 ? String(next) : null });
    // Changing what is listed starts again from the first page.
    const setSearchUrl = (query: string) => setFilters({ search: query || null, page: null });
    const setSearchCategories = (next: string[]) =>
        setFilters({ category: next.join(',') || null, page: null });
    const setOrderBy = (next: WebsiteOrder) =>
        setFilters({ orderBy: next !== 'url' ? next : null, page: null });
    const setLimit = (next: PageSize) => {
        savePageSize(next);
        setLimitState(next);
    };

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

    const requestWebsite = async (url: string, options: NewWebsiteOptions = {}) => {
        try {
            const getter = user ? handlerUserApiRequest<Website> : fetcherApi<Website>;

            const newWebsite = await getter(`/api/websites/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ base_url: url, ...options }),
            });
            // Optimistically update the cache
            mutate(
                {
                    items: [...(data?.items ?? []), newWebsite],
                    count: (data?.count ?? 0) + 1,
                },
                { revalidate: true }
            );
            addAlert('Website created successfully', 'success');
            return newWebsite;
        } catch (error) {
            // The host is not under an allowed domain: the caller decides (a site admin
            // can retry with create_domain), so no alert here.
            if ((error as APIError).details?.code === 'no_parent_domain') {
                throw error;
            }
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
                WebsiteSearch: searchUrl,
                WebsiteCategories: searchCategories,
                WebsiteOrderBy: orderBy,
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

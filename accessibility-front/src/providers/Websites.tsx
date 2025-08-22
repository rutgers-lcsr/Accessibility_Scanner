"use client"
import { APIError, fetcherApi, handleRequest } from '@/lib/api';
import { Website } from '@/lib/types/website';
import { Paged } from '@/lib/types/Paged';
import { useRouter } from 'next/navigation';
import React, { createContext, useContext, ReactNode, useState } from 'react';
import useSWR from 'swr';

type WebsitesContextType = {
    websites: Website[] | null;
    websitesTotal: number;
    error: APIError | null;
    isLoading: boolean;
    WebsitePage: number;
    WebsiteLimit: number;
    setWebsiteSearch: (query: string) => void;
    setWebsitePage: (page: number) => void;
    setWebsiteLimit: (limit: number) => void;
    openWebsite: (id: number) => void;
};

const WebsitesContext = createContext<WebsitesContextType | undefined>(undefined);

export const WebsitesProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const router = useRouter();
    const [page, setPage] = useState(1);
    const [limit, setLimit] = useState(10);
    const [searchUrl, setSearchUrl] = useState('');

    const { data, error, isLoading } = useSWR(`/api/websites/?page=${page}&limit=${limit}${searchUrl ? `&search=${searchUrl}` : ''}`, fetcherApi<Paged<Website>>);

    const openWebsite = (id: number) => {
        // Logic to open the website
        router.push(`/websites?id=${id}`);
    };



    return (
        <WebsitesContext.Provider value={{ websites: data?.items ?? null, websitesTotal: data?.count ?? 0, error, isLoading, openWebsite, WebsitePage: page, WebsiteLimit: limit, setWebsitePage: setPage, setWebsiteLimit: setLimit, setWebsiteSearch: setSearchUrl }}>
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

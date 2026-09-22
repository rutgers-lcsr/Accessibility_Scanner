'use client';
import { APIError, fetcherApi } from '@/lib/api';
import { getInitalPageSize, PageSize, savePageSize } from '@/lib/browser';
import { pageParam, useUrlFilters } from '@/lib/urlFilters';
import { Report } from '@/lib/types/axe';
import { Paged } from '@/lib/types/Paged';
import { PublicUser } from '@/lib/types/user';
import { useRouter } from 'next/navigation';
import React, { createContext, useContext, useState } from 'react';
import useSWR from 'swr';
import { useUser } from './User';

type ReportsContextType = {
    reports: Report[] | undefined;
    reportsTotal: number;
    isLoading: boolean;
    error: APIError | null;
    ReportPage: number;
    ReportLimit: number;
    ReportSearch: string;
    setReportSearch: (query: string) => void;
    setReportPage: (page: number) => void;
    setReportLimit: (limit: PageSize) => void;
    openReport: (id: string) => void;
    mutate: () => void;
};

const ReportsContext = createContext<ReportsContextType | undefined>(undefined);

export const ReportsProvider: React.FC<{ children: React.ReactNode; user: PublicUser | null }> = ({
    children,
    user,
}) => {
    const router = useRouter();
    // Search and page live in the URL (see useUrlFilters) so they are still there after
    // opening a report and coming back; the page size is kept in localStorage.
    const { params, setFilters } = useUrlFilters();
    const page = pageParam(params.get('page'));
    const searchUrl = params.get('search') ?? '';
    const [limit, setLimitState] = useState<PageSize>(getInitalPageSize);

    const setPage = (next: number) => setFilters({ page: next > 1 ? String(next) : null });
    const setSearchUrl = (query: string) => setFilters({ search: query || null, page: null });
    const setLimit = (next: PageSize) => {
        savePageSize(next);
        setLimitState(next);
    };
    const { handlerUserApiRequest } = useUser();
    const { data, error, isLoading, mutate } = useSWR<Paged<Report>>(
        `/api/reports/?page=${page}&limit=${limit}${searchUrl ? `&search=${searchUrl}` : ''}`,
        user ? handlerUserApiRequest : fetcherApi
    );

    const openReport = (id: string) => {
        router.push(`/reports/${id}`);
    };

    return (
        <ReportsContext.Provider
            value={{
                reports: data?.items,
                reportsTotal: data?.count || 0,
                isLoading,
                error,
                ReportPage: page,
                ReportLimit: limit,
                ReportSearch: searchUrl,
                setReportSearch: setSearchUrl,
                setReportPage: setPage,
                setReportLimit: setLimit,
                openReport,
                mutate,
            }}
        >
            {children}
        </ReportsContext.Provider>
    );
};

export const useReports = () => {
    const context = useContext(ReportsContext);
    if (!context) {
        throw new Error('useReports must be used within a ReportsProvider');
    }
    return context;
};

'use client';
import { APIError, fetcherApi } from '@/lib/api';
import { Report } from '@/lib/types/axe';
import { Paged } from '@/lib/types/Paged';
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
    setReportSearch: (query: string) => void;
    setReportPage: (page: number) => void;
    setReportLimit: (limit: number) => void;
    openReport: (id: string) => void;
    mutate: () => void;
};

const ReportsContext = createContext<ReportsContextType | undefined>(undefined);

export const ReportsProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const router = useRouter();
    const [page, setPage] = useState(1);
    const [limit, setLimit] = useState(10);
    const [searchUrl, setSearchUrl] = useState('');
    const { user, handlerUserApiRequest } = useUser();
    const { data, error, isLoading, mutate } = useSWR<Paged<Report>>(
        `/api/reports/?page=${page}&limit=${limit}${searchUrl ? `&search=${searchUrl}` : ''}`,
        user ? handlerUserApiRequest : fetcherApi
    );

    const openReport = (id: string) => {
        router.push(`/reports?id=${id}`);
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

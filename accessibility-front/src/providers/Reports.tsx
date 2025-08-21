"use client"
import { fetcherApi } from '@/lib/api';
import React, { createContext, useContext } from 'react';
import useSWR from 'swr';
import { Report } from '@/lib/types/axe';


type ReportsContextType = {
    reports: Report[] | undefined;
    isLoading: boolean;
    error: any;

    mutate: () => void;
};

const ReportsContext = createContext<ReportsContextType | undefined>(undefined);



export const ReportsProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const { data, error, isLoading, mutate } = useSWR<Report[]>('/api/reports', fetcherApi);


    const fetchReport = (id: string) => {
        return fetcherApi<Report>(`/api/reports/${id}`);
    };

    return (
        <ReportsContext.Provider
            value={{
                reports: data,
                isLoading,
                error,
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
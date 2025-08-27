'use client';
import { APIError } from '@/lib/api';
import { Domain } from '@/lib/types/domain';
import { Paged } from '@/lib/types/Paged';
import React, { createContext, useContext } from 'react';
import useSWR from 'swr';
import { useAlerts } from './Alerts';
import { useUser } from './User';

type DomainContextType = {
    domains: Domain[];
    domainCount: number;
    loadingDomain: boolean;
    domainPage: number;
    domainLimit: number;
    createDomain: (domain: string) => Promise<void>;
    setDomainPage: (page: number) => void;
    setDomainLimit: (limit: number) => void;
    setDomainFilters: (filters: Record<string, string>) => void;
    resetDomainFilters: () => void;
    patchDomain: (id: string, data: Partial<Domain>) => Promise<void>;
    deleteDomain: (id: string) => Promise<void>;
};

export const DomainContext = createContext<DomainContextType | undefined>(undefined);

export const DomainProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const { handlerUserApiRequest } = useUser();
    const { addAlert } = useAlerts();
    const [domainPage, setDomainPage] = React.useState<number>(1);
    const [domainLimit, setDomainLimit] = React.useState<number>(10);
    const [domainFilters, setDomainFilters] = React.useState<Record<string, string>>({});

    const {
        data: domains,
        isLoading: loadingDomain,
        mutate: mutateDomains,
    } = useSWR<Paged<Domain>>(
        `/api/domains/?page=${domainPage}&limit=${domainLimit}&${new URLSearchParams(domainFilters).toString()}`,
        handlerUserApiRequest
    );

    const resetDomainFilters = () => {
        setDomainFilters({});
    };

    const patchDomain = async (id: string, data: Partial<Domain>) => {
        try {
            await handlerUserApiRequest(`/api/domains/${id}`, {
                method: 'PATCH',
                body: JSON.stringify(data),
            });
            mutateDomains();
            addAlert('Domain updated successfully', 'success');
        } catch (error) {
            addAlert(`Failed to update domain ${(error as APIError).getReason()}`, 'error');
            console.error('Failed to patch domain:', error);
        }
    };

    const createDomain = async (domain: string) => {
        try {
            await handlerUserApiRequest(`/api/domains/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ domain: domain }),
            });
            mutateDomains();
            addAlert('Domain created successfully', 'success');
        } catch (error) {
            addAlert('Failed to create domain', 'error');
            console.error('Failed to create domain:', error);
        }
    };
    const deleteDomain = async (id: string) => {
        try {
            await handlerUserApiRequest(`/api/domains/${id}`, {
                method: 'DELETE',
            });
            mutateDomains();
            addAlert('Domain deleted successfully', 'success');
        } catch (error) {
            addAlert('Failed to delete domain', 'error');
            console.error('Failed to delete domain:', error);
        }
    };

    return (
        <DomainContext.Provider
            value={{
                domains: domains?.items || [],
                domainCount: domains?.count || 0,
                loadingDomain,
                domainPage,
                domainLimit,
                createDomain,
                setDomainPage,
                setDomainLimit,
                setDomainFilters,
                resetDomainFilters,
                patchDomain,
                deleteDomain,
            }}
        >
            {children}
        </DomainContext.Provider>
    );
};

export const useDomains = () => {
    const context = useContext(DomainContext);
    if (!context) {
        throw new Error('useDomains must be used within a DomainProvider');
    }
    return context;
};

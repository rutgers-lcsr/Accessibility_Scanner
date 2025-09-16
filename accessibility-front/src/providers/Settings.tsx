'use client';
import { createContext, useContext } from 'react';
import useSWR from 'swr';
import { useUser } from './User';

type Settings = {
    default_tags: string;
    default_rate_limit: number;
};

type SettingsContextType = {
    settings: Settings | undefined;
    all_tags?: string[];
    updateSettings: (newSettings: Partial<Settings>) => void;
    mutate?: () => void;
};

const SettingsContext = createContext<SettingsContextType | undefined>(undefined);

export const SettingsProvider = ({ children }: { children: React.ReactNode }) => {
    const { handlerUserApiRequest } = useUser();
    const {
        data: settings,
        isLoading,
        mutate,
    } = useSWR('/api/settings', handlerUserApiRequest<Settings>);

    const { data: tags } = useSWR('/api/axe/rules/tags/', handlerUserApiRequest<string[]>);

    const updateSettings = async (newSettings: Partial<Settings>) => {
        const update = await handlerUserApiRequest<Settings>('/api/settings', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(newSettings),
        });
        if (mutate) mutate();
        return update;
    };

    return (
        <SettingsContext.Provider value={{ settings, all_tags: tags, updateSettings, mutate }}>
            {children}
        </SettingsContext.Provider>
    );
};

export const useSettings = () => {
    const context = useContext(SettingsContext);
    if (!context) {
        throw new Error('useSettings must be used within a SettingsProvider');
    }
    return context;
};

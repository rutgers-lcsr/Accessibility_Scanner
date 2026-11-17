'use client';
import { createContext, useContext } from 'react';
import useSWR from 'swr';
import { useUser } from './User';

// Every value comes back from the API as a string.
type Settings = {
    default_tags: string;
    default_rate_limit: string;
    default_should_auto_scan: string;
    default_notify_on_completion: string;
    default_email_domain: string;
    default_should_auto_activate: string;
    scan_page_concurrency: string;
    max_pages: string;
    max_depth: string;
    crawl_delay_ms: string;
    admin_digest_enabled: string;
    owner_digest_enabled: string;
    reminder_after_days: string;
    escalate_after_days: string;
    escalation_email: string;
    retention_enabled: string;
    retention_keep_days: string;
    retention_max_days: string;
    document_max_size_mb: string;
    document_checks_per_scan: string;
    document_recheck_days: string;
    link_checks_per_scan: string;
    link_recheck_days: string;
    health_checks_enabled: string;
    health_check_minutes: string;
    health_history_days: string;
    tls_warning_days: string;
    stale_after_days: string;
    sla_critical_days: string;
    sla_serious_days: string;
    sla_moderate_days: string;
    sla_minor_days: string;
    review_interval_days: string;
};

export type SettingKey = keyof Settings;

type SettingsContextType = {
    settings: Settings | undefined;
    all_tags?: string[];
    updateSettings: (newSettings: Partial<Settings>) => Promise<Settings>;
    mutate?: () => void;
};

const SettingsContext = createContext<SettingsContextType | undefined>(undefined);

export const SettingsProvider = ({ children }: { children: React.ReactNode }) => {
    const { handlerUserApiRequest } = useUser();
    const { data: settings, mutate } = useSWR('/api/settings', handlerUserApiRequest<Settings>);

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

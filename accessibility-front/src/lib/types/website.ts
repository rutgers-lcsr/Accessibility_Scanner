import { AxeReportCounts, AxeReportKeys, ReportMinimized, WebsiteAxeReport } from './axe';

export type Website = {
    id: number;
    url: string;
    admin: string;
    users: string[];
    should_email: boolean;
    create_at: string;
    updated_at: string;
    public: boolean;
    last_scanned: string;
    tags: string[];
    default_tags: string[];
    categories: string[];
    description: string;
    report: WebsiteAxeReport;
    report_counts: Record<AxeReportKeys, AxeReportCounts>;
    domain_id: string;
    sites: number[];
    rate_limit: number;
    active: boolean;
};

export type Site = {
    id: number;
    url: string;
    last_scanned: string;
    created_at: string;
    updated_at: string;
    reports: ReportMinimized[];
    tags: string[];
    current_report: ReportMinimized;
    website_id: number;
    active: boolean;
};

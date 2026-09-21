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
    last_scan_status: 'completed' | 'failed' | 'unreachable' | null;
    last_scan_error: string | null;
    // when the admin and users were last emailed about this website
    last_notified: string | null;
    tags: string[];
    default_tags: string[];
    categories: string[];
    // Pages a full scan starts from besides the website URL (sections not linked from the root)
    extra_start_urls: string[];
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
    last_scan_status: 'completed' | 'failed' | null;
    last_scan_error: string | null;
    created_at: string;
    updated_at: string;
    reports: ReportMinimized[];
    tags: string[];
    // null until the page has been audited successfully at least once
    current_report: ReportMinimized | null;
    website_id: number;
    active: boolean;
};

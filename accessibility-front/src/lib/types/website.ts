import { AxeReportCounts, AxeReportKeys, ReportMinimized } from "./axe";

export type Website = {
    id: number;
    base_url: string;
    create_at: string;
    updated_at: string;
    last_scanned: string;
    report_counts: Record<AxeReportKeys, AxeReportCounts>;
    domain_id: string;
    sites: number[];
    active: boolean;
};

export type Site = {
    id: number;
    url: string;
    last_scanned: string;
    created_at: string;
    updated_at: string;
    reports: ReportMinimized[];
    current_report: ReportMinimized;
    website_id: number;
    active: boolean;
};

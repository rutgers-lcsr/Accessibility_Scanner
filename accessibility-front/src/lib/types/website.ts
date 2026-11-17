import { AxeReportCounts, AxeReportKeys, ReportMinimized, WebsiteAxeReport } from './axe';
import { DocumentCounts } from './document';
import { ContentCounts, MediaCounts } from './inventory';
import { LinkCounts } from './link';

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
    // documents (PDF, Word, ...) linked from the website's pages
    documents: DocumentCounts;
    // links found on the website's pages (any host), with how many are broken
    link_counts: LinkCounts;
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
    // Crawl inventories
    media_counts: MediaCounts;
    third_party_count: number;
    content_counts: ContentCounts;
    // Inventory
    lifecycle_status: WebsiteLifecycle;
    sunset_date: string | null; // YYYY-MM-DD
    past_sunset: boolean;
    department: string | null;
    business_owner: string | null;
    audience: WebsiteAudience | null;
    criticality: WebsiteCriticality | null;
};

export type WebsiteLifecycle = 'draft' | 'live' | 'retiring' | 'retired';
export type WebsiteAudience = 'public' | 'students' | 'faculty_staff' | 'internal';
export type WebsiteCriticality = 'high' | 'medium' | 'low';

export const LIFECYCLE_LABELS: Record<WebsiteLifecycle, string> = {
    draft: 'Draft',
    live: 'Live',
    retiring: 'Being retired',
    retired: 'Retired',
};
export const AUDIENCE_LABELS: Record<WebsiteAudience, string> = {
    public: 'Public',
    students: 'Students',
    faculty_staff: 'Faculty and staff',
    internal: 'Internal',
};
export const CRITICALITY_LABELS: Record<WebsiteCriticality, string> = {
    high: 'High',
    medium: 'Medium',
    low: 'Low',
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

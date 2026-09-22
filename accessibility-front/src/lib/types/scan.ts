import { AxeReportCounts, AxeReportKeys, AxeResult } from './axe';

export type scanResponse = {
    message: string;
    info?: string;
    task_id: string;
    status_endpoint: string;
    polling_endpoint: string;
    // quick scans only
    result_endpoint?: string;
    url?: string;
};

export type TaskStatus = {
    state: 'PENDING' | 'PROGRESS' | 'SUCCESS' | 'FAILURE' | 'RETRY' | 'REVOKED';
    status?: string;
    current?: number;
    total?: number;
    // Website scans return website_url/reports_generated/sites_scanned; quick scans
    // return status/url (the report itself comes from the result endpoint).
    result?: {
        status?: string;
        website_url?: string;
        url?: string;
        reports_generated?: number;
        sites_scanned?: number;
        error?: string | null;
    };
};

export type QuickScanRule = AxeResult & { nodes_truncated: number };

// GET /api/scans/quick/<task_id>/ once the task finished.
export type QuickScanResult = {
    task_id: string;
    status: 'completed' | 'failed';
    url: string;
    timestamp: string | null;
    error: string | null;
    response_code: number | null;
    tags: string[];
    report_counts: Record<AxeReportKeys, AxeReportCounts> | null;
    report: { violations: QuickScanRule[]; incomplete: QuickScanRule[] } | null;
    photo_url: string | null;
    photo_omitted: boolean;
    links: number;
    videos: number;
    tabable: boolean | null;
};

// The same endpoint while the task is running (202) or after it failed.
export type QuickScanPending = {
    task_id: string;
    state: string;
    status?: string;
    error?: string;
};

export type QuickScanResponse = QuickScanResult | QuickScanPending;

export function isQuickScanResult(value: QuickScanResponse): value is QuickScanResult {
    return (
        (value as QuickScanResult).status === 'completed' ||
        (value as QuickScanResult).status === 'failed'
    );
}

import { AxeReportCounts } from './axe';
import { HistoryPoint } from './history';

export type ScanStatus = 'completed' | 'failed' | 'unreachable' | null;
export type Impact = 'critical' | 'serious' | 'moderate' | 'minor';

export type DashboardWebsite = {
    id: number;
    url: string;
    categories: string[];
    pages: number;
    pages_audited: number;
    // pages whose latest scan fails at least one rule that still counts
    pages_failing: number;
    last_scanned: string | null;
    last_scan_status: ScanStatus;
    // last scanned more than 30 days ago (services.overview.STALE_SCAN_DAYS)
    stale: boolean;
    violations: AxeReportCounts;
    passes: number;
    incomplete: number;
    documents: number;
    untagged_pdfs: number;
    broken_links: number;
};

export type DashboardCategory = {
    category: string;
    websites: number;
    pages: number;
    violations: AxeReportCounts;
    passes: number;
};

export type DashboardRule = {
    id: string;
    impact: Impact | null;
    help: string | null;
    help_url: string | null;
    description: string | null;
    pages: number;
    occurrences: number;
};

export type Dashboard = {
    generated_at: string;
    days: number;
    totals: {
        websites: number;
        pages: number;
        pages_audited: number;
        pages_failing: number;
        // pages whose latest scan ended on another site: listed apart, not counted
        pages_offsite: number;
        stale_scans: number;
        last_scan: string | null;
        violations: AxeReportCounts;
        passes: number;
        incomplete: number;
        scan_status: Record<string, number>;
        documents: number;
        untagged_pdfs: number;
        broken_links: number;
    };
    websites: DashboardWebsite[];
    categories: DashboardCategory[];
    top_rules: DashboardRule[];
    history: HistoryPoint[];
};

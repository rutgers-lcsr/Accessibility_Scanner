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
    last_scanned: string | null;
    last_scan_status: ScanStatus;
    violations: AxeReportCounts;
    passes: number;
    incomplete: number;
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
        last_scan: string | null;
        violations: AxeReportCounts;
        passes: number;
        incomplete: number;
        scan_status: Record<string, number>;
    };
    websites: DashboardWebsite[];
    categories: DashboardCategory[];
    top_rules: DashboardRule[];
    history: HistoryPoint[];
};

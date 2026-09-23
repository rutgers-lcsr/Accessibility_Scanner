import { AxeReportCounts } from './axe';
import { ScanStatus } from './dashboard';

// Open violations now against an earlier moment; null when there is no baseline (the
// website was never emailed, or has no report that old).
export type Change = { previous: number; current: number; when?: string } | null;

export type Activity = {
    // findings a person marked fixed, false positive or accepted, and the latest verdict
    triaged: number;
    last_triage: string | null;
};

type Counts = {
    pages: number;
    pages_audited: number;
    violations: AxeReportCounts;
    last_scanned: string | null;
    last_notified: string | null;
    activity: Activity;
    since_last_email: Change;
    since_period: Change;
};

export type OwnerWebsite = Counts & {
    id: number;
    url: string;
    description: string | null;
    categories: string[];
    users: string[];
    last_scan_status: ScanStatus;
    passes: number;
    incomplete: number;
    documents: number;
    untagged_pdfs: number;
    active: boolean;
    should_email: boolean;
};

export type Owner = Counts & {
    // null: the websites that have no admin user
    id: number | null;
    username: string | null;
    email: string | null;
    websites_count: number;
    websites: OwnerWebsite[];
};

export type OwnersResponse = {
    generated_at: string;
    period: { days: number; since: string };
    owners: Owner[];
};

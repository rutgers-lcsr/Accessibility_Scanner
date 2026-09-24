import type { AxeReportCounts } from './axe';

export type FindingStatus = 'open' | 'fixed' | 'false_positive' | 'accepted';

// One failing element on one page, tracked across scans (backend models.finding).
export type Finding = {
    id: number;
    site_id: number;
    rule_id: string;
    fingerprint: string;
    impact: 'critical' | 'serious' | 'moderate' | 'minor' | null;
    help: string | null;
    help_url: string | null;
    selector: string | null;
    html: string | null;
    first_seen: string;
    last_seen: string;
    last_report_id: number | null;
    status: FindingStatus;
    status_by: string | null; // username, null when the scanner set it
    status_at: string | null;
    note: string | null;
};

export type FindingPage = {
    site_id: number;
    url: string;
    report_id: number | null;
    findings: Finding[];
};

export type FindingRuleGroup = {
    rule_id: string;
    impact: Finding['impact'];
    help: string | null;
    help_url: string | null;
    counts: Record<FindingStatus, number>;
    pages: FindingPage[];
};

export type WebsiteFindings = {
    count: number;
    rules: FindingRuleGroup[];
};

export type ChangePage = {
    site_id: number;
    url: string;
    report_id: number;
    count: number;
    findings: { id: number; selector: string | null; reopened: boolean }[];
};

export type ChangeRule = {
    rule_id: string;
    impact: Finding['impact'];
    help: string | null;
    help_url: string | null;
    count: number;
    pages: ChangePage[];
};

// What changed between the previous and the latest scan (GET /api/websites/<id>/changes).
export type WebsiteChanges = {
    since: string | null;
    until: string | null;
    previous: AxeReportCounts;
    current: AxeReportCounts;
    new: ChangeRule[];
    fixed: ChangeRule[];
    still_open: ChangeRule[];
    new_count: number;
    reopened_count: number;
    fixed_count: number;
    open_count: number;
    suppressed_count: number;
    regression: boolean;
};

// GET /api/websites/<id>/fix-first: open violations as rules ranked by the pages a fix clears.
export type FixFirstPage = {
    site_id: number;
    url: string;
    report_id: number | null;
    count: number;
};

export type FixFirstExample = {
    finding_id: number;
    site_id: number;
    url: string;
    report_id: number | null;
    selector: string | null;
    html: string | null;
    failure_summary: string | null;
};

export type FixFirstRule = {
    rule_id: string;
    impact: Finding['impact'];
    help: string | null;
    help_url: string | null;
    counts: Record<FindingStatus, number>;
    pages: FixFirstPage[];
    pages_affected: number;
    pages_cleared_percent: number;
    elements: number;
    example: FixFirstExample;
    guide: boolean;
};

export type WebsiteFixFirst = {
    pages_total: number;
    pages_audited: number;
    open_total: number;
    suppressed_rules: number;
    rules: FixFirstRule[];
};

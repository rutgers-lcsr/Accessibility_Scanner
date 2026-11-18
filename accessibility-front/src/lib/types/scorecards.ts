export type Scorecard = {
    department: string;
    websites: number;
    audited: number;
    pages: number;
    critical: number;
    serious: number;
    moderate: number;
    minor: number;
    // Elements marked false positive or accepted: left out of the counts above.
    suppressed: number;
    overdue: number;
    due_soon: number;
    active_exceptions: number;
    clean_percent: number | null;
    reviewed_percent: number | null;
    median_days_to_fix: number | null;
    uptime_30d: number | null;
    down: number;
    tls_problems: number;
    stale_pages: number;
    mixed_content_pages: number;
    media_missing_captions: number;
    website_ids: number[];
};

export type ScorecardsResponse = {
    generated_at: string;
    departments: Scorecard[];
    totals: Scorecard | null;
};

export type ComplianceRow = {
    id: number;
    url: string;
    department: string | null;
    business_owner: string | null;
    admin: string | null;
    lifecycle_status: string;
    criticality: string | null;
    audience: string | null;
    last_scanned: string | null;
    pages: number;
    critical: number;
    serious: number;
    moderate: number;
    minor: number;
    // Elements marked false positive or accepted: left out of the counts above.
    suppressed: number;
    overdue: number;
    due_soon: number;
    excepted: number;
    active_exceptions: number;
    pending_exceptions: number;
    last_review: string | null;
    review_due: boolean;
    median_days_to_fix: number | null;
    uptime_30d: number | null;
    up: boolean | null;
    tls_valid: boolean | null;
    tls_expires_at: string | null;
    https_redirect: boolean | null;
    security_headers: number | null;
    platform: string | null;
    stale_pages: number;
    mixed_content_pages: number;
    media_missing_captions: number;
    media_unchecked: number;
    unregistered_third_parties: number;
};

export type ComplianceReportResponse = {
    generated_at: string;
    department: string | null;
    summary: Scorecard | null;
    websites: ComplianceRow[];
};

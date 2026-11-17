export type ExceptionKind =
    'archived' | 'third_party' | 'undue_burden' | 'fundamental_alteration' | 'other';
export type ExceptionStatus = 'requested' | 'approved' | 'rejected' | 'expired';

export const EXCEPTION_KIND_LABELS: Record<ExceptionKind, string> = {
    archived: 'Archived content',
    third_party: 'Third-party content',
    undue_burden: 'Undue burden',
    fundamental_alteration: 'Fundamental alteration',
    other: 'Other',
};

export const EXCEPTION_STATUS_COLORS: Record<ExceptionStatus, string> = {
    requested: 'orange',
    approved: 'green',
    rejected: 'red',
    expired: 'default',
};

export type ComplianceException = {
    id: number;
    website_id: number;
    website_url: string | null;
    rule_id: string | null;
    url_prefix: string | null;
    kind: ExceptionKind;
    reason: string;
    status: ExceptionStatus;
    requested_by: string | null;
    requested_at: string;
    decided_by: string | null;
    decided_at: string | null;
    decision_note: string | null;
    expires_on: string | null;
};

export type ReviewResult = 'pass' | 'fail' | 'not_applicable' | 'not_tested';

export const REVIEW_RESULT_LABELS: Record<ReviewResult, string> = {
    pass: 'Pass',
    fail: 'Fail',
    not_applicable: 'Not applicable',
    not_tested: 'Not tested',
};

export type ChecklistItem = { key: string; title: string; wcag: string; how: string };

export type ReviewEntry = { result: ReviewResult; notes: string | null; pages: string[] };

export type ManualReview = {
    id: number;
    website_id: number;
    reviewer: string | null;
    source: 'person' | 'agent';
    tool: string | null;
    status: 'in_progress' | 'completed';
    pages: string[];
    results: Record<string, ReviewEntry>;
    counts: Record<ReviewResult, number>;
    summary: string | null;
    started_at: string;
    completed_at: string | null;
};

export type WebsiteCompliance = {
    overdue: number;
    due_soon: number;
    excepted: number;
    active_exceptions: number;
    pending_exceptions: number;
    last_review: string | null;
    review_due: boolean;
};

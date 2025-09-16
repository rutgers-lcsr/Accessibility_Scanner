export type AxeCheck = {
    id: string; // Unique identifier for the check (e.g., 'color-contrast')
    impact?: 'minor' | 'moderate' | 'serious' | 'critical'; // Severity of the issue
    message: string; // Human-readable message describing the check
    data: Record<string, unknown>; // Additional data relevant to the check
    relatedNodes: Array<Record<string, unknown>>; // Nodes related to the check
};

export type AxeNode = {
    html: string; // HTML snippet of the node
    target: string[]; // CSS selectors identifying the node
    failureSummary?: string; // Summary of why the node failed
    any: AxeCheck[]; // Checks that must pass for the node to pass
    all: AxeCheck[]; // Checks that must all pass for the node to pass
    none: AxeCheck[]; // Checks that must not be present for the node to pass
};

export type AxeResult = {
    id: number;
    impact?: 'minor' | 'moderate' | 'serious' | 'critical';
    description: string;
    help: string;
    helpUrl: string;
    tags: string[];
    nodes: AxeNode[];
};

export type AxeReport = {
    violations: AxeResult[];
    passes: AxeResult[];
    inapplicable: AxeResult[];
    incomplete: AxeResult[];
};

export type AxeReportCounts = {
    total: number;
    critical: number;
    serious: number;
    moderate: number;
    minor: number;
};

export type AxeReportKeys = 'violations' | 'passes' | 'inapplicable' | 'incomplete';

export type ReportMinimized = {
    id: number;
    url: string;
    report_counts: Record<AxeReportKeys, AxeReportCounts>;
    timestamp: string;
};

export type Report = {
    id: number;
    url: string;
    site_id: number;
    base_url: string;
    timestamp: string;
    report: AxeReport;
    report_counts: Record<AxeReportKeys, AxeReportCounts>;
    current_report: ReportMinimized;
    links: string[];
    videos: string[];
    imgs: string[];
    tabable: boolean;
    created_at: string;
    updated_at: string;
};

export type CheckTemplate = {
    name: string;
    rule_id: number;
    type: 'all' | 'any' | 'none';
    description: string;
    evaluate: string; // JavaScript function as a string
    options?: Record<string, unknown>;
    pass_text: string;
    fail_text: string;
    imcomplete_text?: string;
    impact: 'minor' | 'moderate' | 'serious' | 'critical';
};

export type Check = {
    id: number; // Unique identifier for the check (e.g., 'color-contrast')
    name: string; // Human-readable name of the check
    description: string; // Description of what the check does
    evaluate: string; // JavaScript function as a string to evaluate the check
    options: Record<string, unknown>; // Options for the check
    pass_text: string; // Text to display when the check passes
    fail_text: string; // Text to display when the check fails
    impact: 'minor' | 'moderate' | 'serious' | 'critical'; // Severity of the issue
    incomplete_text: string; // Whether the check is incomplete
};

export type RuleTemplate = {
    name: string;
    description: string;
    matches?: string;
    selector?: string;
    help: string;
    help_url: string;
    tags: string[];
    exclude_hidden: boolean;
    impact: 'minor' | 'moderate' | 'serious' | 'critical';
};
export type Rule = {
    id: number;
    name: string;
    description: string;
    matches: string; // JavaScript function as a string
    selector: string; // CSS selector
    enabled: boolean;
    exclude_hidden: boolean;
    help: string;
    help_url: string;
    tags: string[]; // Tags associated with the rule
    all: number[]; // IDs of checks that must all pass
    any: number[]; // IDs of checks that must pass
    none: number[]; // IDs of checks that must not be present
    impact: 'minor' | 'moderate' | 'serious' | 'critical';
};
export type RulesChecks = {
    all: Check[];
    any: Check[];
    none: Check[];
};

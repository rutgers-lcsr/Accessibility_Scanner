export type AxeCheck = {
    id: string; // Unique identifier for the check (e.g., 'color-contrast')
    impact?: "minor" | "moderate" | "serious" | "critical"; // Severity of the issue
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
    impact?: "minor" | "moderate" | "serious" | "critical";
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

export type AxeReportKeys = "violations" | "passes" | "inapplicable" | "incomplete";

export type ReportMinimized = {
    id: number;
    url: string;
    report_counts: Record<AxeReportKeys, AxeReportCounts>;
    timestamp: string;
};

export type Report = {
    id: number;
    url: string;
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

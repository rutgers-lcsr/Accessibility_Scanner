import { AxeReportCounts } from './axe';

// A single point in an accessibility history series. Per-URL points carry an
// `id` + `timestamp` (from /api/sites/<id>/history); per-website aggregate points
// carry a `date` (from /api/websites/<id>/history). report_counts is keyed by the
// real backend categories: violations, passes, incomplete, inaccessible.
export type HistoryPoint = {
    id?: number;
    timestamp?: string;
    date?: string;
    report_counts: Record<string, AxeReportCounts>;
};

// The four categories the history charts plot, in render order.
export const HISTORY_CATEGORIES = [
    'violations',
    'inaccessible',
    'incomplete',
    'passes',
] as const;

export type HistoryCategory = (typeof HISTORY_CATEGORIES)[number];

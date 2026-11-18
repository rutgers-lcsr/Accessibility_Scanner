'use client';

import { HISTORY_CATEGORIES, HistoryCategory, HistoryPoint } from '@/lib/types/history';
import { format } from 'date-fns';
import dynamic from 'next/dynamic';

// @ant-design/plots touches `window` at import time, so load it client-only to
// avoid SSR errors in the Next.js App Router.
const Line = dynamic(() => import('@ant-design/plots').then((m) => m.Line), {
    ssr: false,
});

type Props = {
    data: HistoryPoint[];
    // Which field on each point holds the x value: per-URL points use `timestamp`,
    // per-website aggregate points use `date`.
    x: 'timestamp' | 'date';
    compact?: boolean;
    // What to plot: the four result categories (default), or open violations split by
    // severity. The latter keeps every line on one scale; passes are an order of
    // magnitude larger than violations and flatten them when plotted together.
    series?: 'categories' | 'violations';
};

const CATEGORY_LABELS: Record<HistoryCategory, string> = {
    violations: 'Violations',
    incomplete: 'Incomplete',
    passes: 'Passes',
};

// Severity-aligned palette (matches the red/yellow used elsewhere), green for passes.
// Order matches HISTORY_CATEGORIES, which is the order categories first appear in the data.
const CATEGORY_COLORS = ['#dc2626', '#ca8a04', '#16a34a'];

const IMPACTS = ['critical', 'serious', 'moderate', 'minor'] as const;
const IMPACT_LABELS: Record<(typeof IMPACTS)[number], string> = {
    critical: 'Critical',
    serious: 'Serious',
    moderate: 'Moderate',
    minor: 'Minor',
};
// Severity is ordered, so it takes one hue stepped by lightness (dark = worst), validated
// as an ordinal ramp: monotone lightness, visible steps, light end above 2:1 on white.
const IMPACT_COLORS = ['#7f1d1d', '#b91c1c', '#ef4444', '#f87171'];

function HistoryChart({ data, x, compact = false, series = 'categories' }: Props) {
    if (!data || data.length < 2) {
        return (
            <div className="flex items-center justify-center p-6 text-gray-500">
                Not enough history yet — at least two scans are needed to show a trend.
            </div>
        );
    }

    const labelFor = (rawX: string) => {
        // A bare date ("2026-09-28") parses as midnight UTC, which is the evening before
        // in New Jersey: read it as a local date.
        const d = /^\d{4}-\d{2}-\d{2}$/.test(rawX) ? new Date(`${rawX}T00:00:00`) : new Date(rawX);
        return x === 'date' ? format(d, 'MMM d, yyyy') : format(d, 'MMM d, HH:mm');
    };

    // Long format: one row per (point, series) so antd-plots draws one line per series.
    const chartData = data.flatMap((point) => {
        const rawX = (x === 'date' ? point.date : point.timestamp) ?? '';
        const label = rawX ? labelFor(rawX) : '';
        if (series === 'violations') {
            return IMPACTS.map((impact) => ({
                x: label,
                category: IMPACT_LABELS[impact],
                value: point.report_counts?.violations?.[impact] ?? 0,
            }));
        }
        return HISTORY_CATEGORIES.map((cat) => ({
            x: label,
            category: CATEGORY_LABELS[cat],
            value: point.report_counts?.[cat]?.total ?? 0,
        }));
    });

    const config = {
        data: chartData,
        xField: 'x',
        yField: 'value',
        colorField: 'category',
        height: compact ? 220 : 360,
        scale: { color: { range: series === 'violations' ? IMPACT_COLORS : CATEGORY_COLORS } },
        axis: { y: { title: 'Count' }, x: { title: false } },
        legend: { color: { position: 'top' as const } },
    };

    // The chart is a canvas: give screen readers the trend it shows in words.
    const first = data[0];
    const last = data[data.length - 1];
    const firstX = (x === 'date' ? first.date : first.timestamp) ?? '';
    const lastX = (x === 'date' ? last.date : last.timestamp) ?? '';
    const summary = `Rule failures (a rule failing on one page counts once) went from ${first.report_counts?.violations?.total ?? 0} on ${
        firstX ? labelFor(firstX) : 'the first scan'
    } to ${last.report_counts?.violations?.total ?? 0} on ${firstX ? labelFor(lastX) : 'the last scan'}, across ${data.length} scans.`;

    return (
        <figure style={{ margin: 0 }}>
            <Line {...config} />
            <figcaption className="sr-only">{summary}</figcaption>
        </figure>
    );
}

export default HistoryChart;

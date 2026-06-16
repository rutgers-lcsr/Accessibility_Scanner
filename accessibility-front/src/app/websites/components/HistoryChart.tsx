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
};

const CATEGORY_LABELS: Record<HistoryCategory, string> = {
    violations: 'Violations',
    inaccessible: 'Inaccessible',
    incomplete: 'Incomplete',
    passes: 'Passes',
};

// Severity-aligned palette (matches the red/orange/yellow used elsewhere), green for passes.
// Order matches HISTORY_CATEGORIES, which is the order categories first appear in the data.
const CATEGORY_COLORS = ['#dc2626', '#ea580c', '#ca8a04', '#16a34a'];

function HistoryChart({ data, x, compact = false }: Props) {
    if (!data || data.length < 2) {
        return (
            <div className="flex items-center justify-center p-6 text-gray-500">
                Not enough history yet — at least two scans are needed to show a trend.
            </div>
        );
    }

    const labelFor = (rawX: string) => {
        const d = new Date(rawX);
        return x === 'date' ? format(d, 'MMM d, yyyy') : format(d, 'MMM d, HH:mm');
    };

    // Long format: one row per (point, category) so antd-plots draws one line per category.
    const chartData = data.flatMap((point) => {
        const rawX = (x === 'date' ? point.date : point.timestamp) ?? '';
        const label = rawX ? labelFor(rawX) : '';
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
        scale: { color: { range: CATEGORY_COLORS } },
        axis: { y: { title: 'Count' }, x: { title: false } },
        legend: { color: { position: 'top' as const } },
    };

    return <Line {...config} />;
}

export default HistoryChart;

'use client';

import HistoryChart from '@/app/websites/components/HistoryChart';
import PageError from '@/components/PageError';
import PageHeading from '@/components/PageHeading';
import ImpactTiles from '@/components/ImpactTiles';
import PageLoading from '@/components/PageLoading';
import ScanStatusTag from '@/components/ScanStatusTag';
import {
    Dashboard as DashboardType,
    DashboardCategory,
    DashboardRule,
    DashboardWebsite,
} from '@/lib/types/dashboard';
import { IMPACTS, ImpactTag } from '@/lib/impact';
import { useUser } from '@/providers/User';
import { CheckCircleOutlined, WarningOutlined } from '@ant-design/icons';
import { Alert, Card, Select, Statistic, Table, TableColumnType, Tag } from 'antd';
import Content from '@/components/Content';
import { formatDate } from 'date-fns';
import Link from 'next/link';
import { ReactNode, useState } from 'react';
import useSWR from 'swr';

const DAY_OPTIONS = [
    { value: 30, label: 'Last 30 days' },
    { value: 90, label: 'Last 90 days' },
    { value: 180, label: 'Last 6 months' },
    { value: 365, label: 'Last year' },
];

function passRate(passes: number, violations: number): number | null {
    const total = passes + violations;
    return total === 0 ? null : Math.round((passes / total) * 100);
}

function SectionTitle({ id, children }: { id: string; children: ReactNode }) {
    return (
        <h2 id={id} className="mb-3 text-xl font-semibold text-gray-800">
            {children}
        </h2>
    );
}

const numberSorter =
    (pick: (row: DashboardWebsite) => number) => (a: DashboardWebsite, b: DashboardWebsite) =>
        pick(a) - pick(b);

function Dashboard() {
    const { handlerUserApiRequest } = useUser();
    const [days, setDays] = useState(90);

    const { data, error, isLoading } = useSWR(
        `/api/dashboard?days=${days}`,
        handlerUserApiRequest<DashboardType>
    );

    if (error) return <PageError status={500} title="Error loading the dashboard" />;
    if (isLoading || !data) return <PageLoading />;

    const { totals } = data;
    const attention = (totals.scan_status.failed ?? 0) + (totals.scan_status.unreachable ?? 0);
    const rate = passRate(totals.passes, totals.violations.total);

    const websiteColumns: TableColumnType<DashboardWebsite>[] = [
        {
            title: 'Website',
            dataIndex: 'url',
            key: 'url',
            render: (url: string, row) => <Link href={`/websites/${row.id}`}>{url}</Link>,
            sorter: (a, b) => a.url.localeCompare(b.url),
        },
        {
            title: 'Categories',
            dataIndex: 'categories',
            key: 'categories',
            render: (categories: string[]) =>
                categories.length ? (
                    categories.map((c) => <Tag key={c}>{c}</Tag>)
                ) : (
                    <span className="text-gray-400">—</span>
                ),
        },
        {
            title: 'Pages',
            key: 'pages',
            render: (_, row) => `${row.pages_audited} / ${row.pages}`,
            sorter: numberSorter((r) => r.pages),
        },
        {
            // Documents and untagged PDFs share a column so the table fits beside the sidebar.
            title: 'Documents',
            key: 'documents',
            align: 'right',
            render: (_, row) => (
                <>
                    {row.documents}
                    {row.untagged_pdfs > 0 && (
                        <strong className="block text-xs whitespace-nowrap text-[#c2410c]">
                            {row.untagged_pdfs} untagged PDF{row.untagged_pdfs === 1 ? '' : 's'}
                        </strong>
                    )}
                </>
            ),
            // Sorting descending puts the websites with the most untagged PDFs first.
            sorter: (a, b) => a.untagged_pdfs - b.untagged_pdfs || a.documents - b.documents,
        },
        ...IMPACTS.map<TableColumnType<DashboardWebsite>>((impact) => ({
            title: impact.label,
            key: impact.key,
            align: 'right',
            render: (_, row) => row.violations[impact.key],
            sorter: numberSorter((r) => r.violations[impact.key]),
        })),
        {
            title: 'Total',
            key: 'total',
            align: 'right',
            render: (_, row) => <strong>{row.violations.total}</strong>,
            sorter: numberSorter((r) => r.violations.total),
            defaultSortOrder: 'descend',
        },
        {
            title: 'Pass rate',
            key: 'pass_rate',
            align: 'right',
            render: (_, row) => {
                const value = passRate(row.passes, row.violations.total);
                return value === null ? <span className="text-gray-400">—</span> : `${value}%`;
            },
            sorter: numberSorter((r) => passRate(r.passes, r.violations.total) ?? -1),
        },
        {
            // When it ran and how it ended, in one column.
            title: 'Last scan',
            key: 'last_scanned',
            render: (_, row) => (
                <div className="flex flex-col items-start gap-1">
                    {row.last_scanned && (
                        <span className="whitespace-nowrap">
                            {formatDate(new Date(row.last_scanned), 'MMM d, yyyy')}
                        </span>
                    )}
                    <ScanStatusTag status={row.last_scan_status} lastScanned={row.last_scanned} />
                </div>
            ),
            sorter: (a, b) => (a.last_scanned ?? '').localeCompare(b.last_scanned ?? ''),
        },
    ];

    const ruleColumns: TableColumnType<DashboardRule>[] = [
        {
            title: 'Issue',
            key: 'help',
            render: (_, rule) => (
                <>
                    {rule.help_url ? (
                        <a href={rule.help_url} target="_blank" rel="noopener noreferrer">
                            {rule.help ?? rule.id}
                        </a>
                    ) : (
                        (rule.help ?? rule.id)
                    )}
                    <div className="text-xs text-gray-500">{rule.id}</div>
                </>
            ),
        },
        {
            title: 'Impact',
            key: 'impact',
            render: (_, rule) => <ImpactTag impact={rule.impact} />,
        },
        {
            title: 'Pages affected',
            dataIndex: 'pages',
            key: 'pages',
            align: 'right',
            sorter: (a, b) => a.pages - b.pages,
        },
        {
            title: 'Occurrences',
            dataIndex: 'occurrences',
            key: 'occurrences',
            align: 'right',
            sorter: (a, b) => a.occurrences - b.occurrences,
        },
    ];

    const categoryColumns: TableColumnType<DashboardCategory>[] = [
        { title: 'Category', dataIndex: 'category', key: 'category' },
        { title: 'Websites', dataIndex: 'websites', key: 'websites', align: 'right' },
        { title: 'Pages', dataIndex: 'pages', key: 'pages', align: 'right' },
        ...IMPACTS.map<TableColumnType<DashboardCategory>>((impact) => ({
            title: impact.label,
            key: impact.key,
            align: 'right',
            render: (_, row) => row.violations[impact.key],
        })),
        {
            title: 'Total',
            key: 'total',
            align: 'right',
            render: (_, row) => <strong>{row.violations.total}</strong>,
            sorter: (a, b) => a.violations.total - b.violations.total,
            defaultSortOrder: 'descend',
        },
    ];

    return (
        <>
            <PageHeading
                title="Accessibility Dashboard"
                subtitle="Every website you can see, at a glance"
                actions={
                    <Select
                        aria-label="History range"
                        value={days}
                        options={DAY_OPTIONS}
                        onChange={setDays}
                        style={{ width: 160 }}
                    />
                }
            />
            <Content className="mb-8 p-4">
                {totals.websites === 0 ? (
                    <Alert
                        type="info"
                        showIcon
                        title="No websites yet"
                        description={
                            <>
                                Nothing is visible to you yet. Add or request a website on the{' '}
                                <Link href="/websites">Websites</Link> page to start tracking it
                                here.
                            </>
                        }
                    />
                ) : (
                    <div className="flex flex-col gap-8">
                        <section aria-labelledby="dash-overview">
                            <SectionTitle id="dash-overview">Overview</SectionTitle>
                            <div className="grid grid-cols-2 gap-3 md:grid-cols-3 md:gap-4 xl:grid-cols-5">
                                <Card className="h-full">
                                    <Statistic title="Websites" value={totals.websites} />
                                </Card>
                                <Card className="h-full">
                                    <Statistic
                                        title="Pages audited"
                                        value={totals.pages_audited}
                                        suffix={`/ ${totals.pages}`}
                                    />
                                </Card>
                                <Card className="h-full">
                                    <Statistic
                                        title="Pass rate (rules passed vs. violated)"
                                        value={rate ?? '—'}
                                        suffix={rate === null ? undefined : '%'}
                                    />
                                </Card>
                                <Card className="h-full">
                                    <Statistic
                                        title="Scans needing attention"
                                        value={attention}
                                        prefix={
                                            attention > 0 ? (
                                                <WarningOutlined />
                                            ) : (
                                                <CheckCircleOutlined />
                                            )
                                        }
                                        styles={{
                                            content: {
                                                color: attention > 0 ? '#c2410c' : '#15803d',
                                            },
                                        }}
                                    />
                                    <div className="mt-1 text-xs text-gray-500">
                                        {attention > 0
                                            ? 'Websites whose last scan failed or could not reach the site'
                                            : totals.last_scan
                                              ? `Last scan ${formatDate(new Date(totals.last_scan), 'MMM d, yyyy HH:mm')}`
                                              : 'No scans yet'}
                                    </div>
                                </Card>
                                <Card className="h-full">
                                    <Statistic title="Documents found" value={totals.documents} />
                                    <div className="mt-1 text-xs text-gray-500">
                                        {totals.untagged_pdfs} untagged PDF
                                        {totals.untagged_pdfs === 1 ? '' : 's'}
                                    </div>
                                </Card>
                            </div>
                        </section>

                        <section aria-labelledby="dash-violations">
                            <SectionTitle id="dash-violations">
                                Open violations{' '}
                                <span className="text-base font-normal text-gray-500">
                                    (latest scan of every page)
                                </span>
                            </SectionTitle>
                            <ImpactTiles counts={totals.violations} />
                            <p className="mt-3 text-sm text-gray-600">
                                {totals.violations.total} violations across {totals.pages_audited}{' '}
                                audited pages
                                {totals.pages_audited > 0 &&
                                    ` (${(totals.violations.total / totals.pages_audited).toFixed(1)} per page)`}
                                {totals.incomplete > 0 &&
                                    `, plus ${totals.incomplete} checks that need manual review`}
                                .
                            </p>
                        </section>

                        <section aria-labelledby="dash-trend">
                            <SectionTitle id="dash-trend">
                                Open violations over time{' '}
                                <span className="text-base font-normal text-gray-500">
                                    (by severity)
                                </span>
                            </SectionTitle>
                            <Card>
                                <HistoryChart data={data.history} x="date" series="violations" />
                            </Card>
                        </section>

                        <section aria-labelledby="dash-websites">
                            <SectionTitle id="dash-websites">
                                Websites ranked by open violations
                            </SectionTitle>
                            <Table<DashboardWebsite>
                                rowKey="id"
                                columns={websiteColumns}
                                dataSource={data.websites}
                                pagination={{ pageSize: 10, hideOnSinglePage: true }}
                                scroll={{ x: true }}
                                size="middle"
                            />
                        </section>

                        <section aria-labelledby="dash-rules">
                            <SectionTitle id="dash-rules">Most common issues</SectionTitle>
                            <Table<DashboardRule>
                                rowKey="id"
                                columns={ruleColumns}
                                dataSource={data.top_rules}
                                pagination={false}
                                size="middle"
                            />
                        </section>

                        {data.categories.length > 0 && (
                            <section aria-labelledby="dash-categories">
                                <SectionTitle id="dash-categories">By category</SectionTitle>
                                <Table<DashboardCategory>
                                    rowKey="category"
                                    columns={categoryColumns}
                                    dataSource={data.categories}
                                    pagination={false}
                                    size="middle"
                                />
                            </section>
                        )}
                    </div>
                )}
            </Content>
        </>
    );
}

export default Dashboard;

'use client';
import Content from '@/components/Content';
import PageError from '@/components/PageError';
import PageHeading from '@/components/PageHeading';
import PageLoading from '@/components/PageLoading';
import { ComplianceReportResponse, ComplianceRow } from '@/lib/types/scorecards';
import { useUser } from '@/providers/User';
import { Button, Checkbox, Descriptions, Table, Tag } from 'antd';
import { useSearchParams } from 'next/navigation';
import { useState } from 'react';
import useSWR from 'swr';

const day = (value: string | null) => (value ? new Date(value).toLocaleDateString() : '—');
const pct = (value: number | null | undefined) =>
    value === null || value === undefined ? '—' : `${value}%`;
const yesNo = (value: boolean | null, good = true) =>
    value === null ? (
        '—'
    ) : value === good ? (
        <Tag color="green">{value ? 'Yes' : 'No'}</Tag>
    ) : (
        <Tag color="red">{value ? 'Yes' : 'No'}</Tag>
    );

// A printable compliance report over the websites the caller can see, optionally one
// department: summary first, then one row per website. Print it to PDF from the
// browser, or download the same rows as CSV.
function ComplianceReport() {
    const { handlerUserApiRequest } = useUser();
    const department = useSearchParams().get('department');
    const [includeRetired, setIncludeRetired] = useState(false);
    const query = `${department ? `department=${encodeURIComponent(department)}&` : ''}${includeRetired ? 'include_retired=true' : ''}`;
    const { data, error } = useSWR(
        `/api/compliance-report/?${query}`,
        handlerUserApiRequest<ComplianceReportResponse>
    );

    if (error) return <PageError status={500} title="Error loading the compliance report" />;

    const s = data?.summary;
    return (
        <>
            <PageHeading
                title={`Accessibility compliance report${department ? `: ${department}` : ''}`}
                subtitle={
                    data ? `Generated ${new Date(data.generated_at).toLocaleString()}` : undefined
                }
                actions={
                    <div className="flex flex-wrap items-center gap-2 print:hidden">
                        <Checkbox
                            checked={includeRetired}
                            onChange={(e) => setIncludeRetired(e.target.checked)}
                        >
                            Include retired websites
                        </Checkbox>
                        <Button href={`/api/compliance-report/?${query}&format=csv`}>
                            Download CSV
                        </Button>
                        <Button type="primary" onClick={() => window.print()}>
                            Print or save as PDF
                        </Button>
                    </div>
                }
            />
            <Content className="p-6">
                {!data ? (
                    <PageLoading />
                ) : (
                    <>
                        {s && (
                            <section aria-labelledby="report-summary" className="mb-8">
                                <h2 id="report-summary" className="mb-3 text-xl font-semibold">
                                    Summary
                                </h2>
                                <Descriptions
                                    bordered
                                    size="small"
                                    column={{ xs: 1, sm: 2, lg: 3 }}
                                    items={[
                                        {
                                            key: 'w',
                                            label: 'Websites',
                                            children: `${s.websites} (${s.audited} scanned)`,
                                        },
                                        { key: 'p', label: 'Pages audited', children: s.pages },
                                        {
                                            key: 'i',
                                            label: 'Open issues by impact',
                                            children: `${s.critical} critical, ${s.serious} serious, ${s.moderate} moderate, ${s.minor} minor`,
                                        },
                                        {
                                            key: 'o',
                                            label: 'Past their deadline',
                                            children: s.overdue,
                                        },
                                        {
                                            key: 'd',
                                            label: 'Due in the next 2 weeks',
                                            children: s.due_soon,
                                        },
                                        {
                                            key: 'e',
                                            label: 'Active exceptions',
                                            children: s.active_exceptions,
                                        },
                                        {
                                            key: 'c',
                                            label: 'Websites with no critical or serious issues',
                                            children: pct(s.clean_percent),
                                        },
                                        {
                                            key: 'r',
                                            label: 'Websites with a current manual review',
                                            children: pct(s.reviewed_percent),
                                        },
                                        {
                                            key: 'f',
                                            label: 'Median days to fix (last year)',
                                            children: s.median_days_to_fix ?? '—',
                                        },
                                        {
                                            key: 'u',
                                            label: 'Average uptime (30 days)',
                                            children: pct(s.uptime_30d),
                                        },
                                        {
                                            key: 't',
                                            label: 'Certificate problems',
                                            children: s.tls_problems,
                                        },
                                        {
                                            key: 'm',
                                            label: 'Videos without captions',
                                            children: s.media_missing_captions,
                                        },
                                    ]}
                                />
                                <p className="mt-2 text-xs text-gray-500">
                                    Issues are counted per rule per page from the latest scan, as on
                                    the website pages. Automated scans find about a third of
                                    accessibility problems; manual reviews cover the rest.
                                </p>
                            </section>
                        )}
                        <section aria-labelledby="report-websites">
                            <h2 id="report-websites" className="mb-3 text-xl font-semibold">
                                Websites
                            </h2>
                            <Table<ComplianceRow>
                                rowKey="id"
                                size="small"
                                pagination={false}
                                dataSource={data.websites}
                                locale={{ emptyText: 'No websites.' }}
                                columns={[
                                    {
                                        title: 'Website',
                                        key: 'url',
                                        render: (_, r) => (
                                            <>
                                                <a href={`/websites/${r.id}`} className="break-all">
                                                    {r.url}
                                                </a>
                                                <div className="text-xs text-gray-500">
                                                    {[
                                                        r.department,
                                                        r.business_owner ?? r.admin,
                                                        r.lifecycle_status !== 'live' &&
                                                            r.lifecycle_status,
                                                    ]
                                                        .filter(Boolean)
                                                        .join(' · ')}
                                                </div>
                                            </>
                                        ),
                                    },
                                    {
                                        title: 'Scanned',
                                        dataIndex: 'last_scanned',
                                        key: 'scanned',
                                        render: day,
                                    },
                                    {
                                        title: 'Critical / serious',
                                        key: 'cs',
                                        render: (_, r) => `${r.critical} / ${r.serious}`,
                                    },
                                    {
                                        title: 'Overdue',
                                        dataIndex: 'overdue',
                                        key: 'overdue',
                                        render: (v: number) => (v ? <Tag color="red">{v}</Tag> : 0),
                                    },
                                    {
                                        title: 'Exceptions',
                                        key: 'exc',
                                        render: (_, r) =>
                                            `${r.active_exceptions}${r.pending_exceptions ? ` (+${r.pending_exceptions} pending)` : ''}`,
                                    },
                                    {
                                        title: 'Manual review',
                                        key: 'review',
                                        render: (_, r) => (
                                            <>
                                                {day(r.last_review)}{' '}
                                                {r.review_due && <Tag color="orange">Due</Tag>}
                                            </>
                                        ),
                                    },
                                    {
                                        title: 'Uptime',
                                        dataIndex: 'uptime_30d',
                                        key: 'uptime',
                                        render: pct,
                                    },
                                    {
                                        title: 'Certificate',
                                        key: 'tls',
                                        render: (_, r) => yesNo(r.tls_valid),
                                    },
                                    {
                                        title: 'Upkeep',
                                        key: 'upkeep',
                                        render: (_, r) => (
                                            <span className="text-xs">
                                                {r.stale_pages} stale · {r.mixed_content_pages}{' '}
                                                mixed ·{' '}
                                                {r.media_missing_captions + r.media_unchecked} media
                                                to check · {r.unregistered_third_parties}{' '}
                                                unregistered third parties
                                            </span>
                                        ),
                                    },
                                ]}
                            />
                        </section>
                    </>
                )}
            </Content>
        </>
    );
}

export default ComplianceReport;

'use client';
import Content from '@/components/Content';
import PageError from '@/components/PageError';
import PageHeading from '@/components/PageHeading';
import PageLoading from '@/components/PageLoading';
import { Scorecard, ScorecardsResponse } from '@/lib/types/scorecards';
import { useUser } from '@/providers/User';
import { Button, Table, Tag } from 'antd';
import Link from 'next/link';
import useSWR from 'swr';

const pct = (value: number | null) => (value === null ? '—' : `${value}%`);

export const reportHref = (department?: string) =>
    `/scorecards/report${department ? `?department=${encodeURIComponent(department)}` : ''}`;

// One row per department over the websites you can see (retired ones left out), worst
// first: overdue issues, then critical and serious ones.
function Scorecards() {
    const { handlerUserApiRequest } = useUser();
    const { data, error } = useSWR('/api/scorecards/', handlerUserApiRequest<ScorecardsResponse>);

    if (error) return <PageError status={500} title="Error loading scorecards" />;

    const columns = [
        {
            title: 'Department',
            dataIndex: 'department',
            key: 'department',
            render: (department: string, card: Scorecard) =>
                card.department === 'All departments' ? (
                    <strong>{department}</strong>
                ) : (
                    <Link href={reportHref(department)}>{department}</Link>
                ),
        },
        {
            title: 'Websites',
            key: 'websites',
            render: (_: unknown, c: Scorecard) => (
                <>
                    {c.websites}
                    {c.audited < c.websites && (
                        <div className="text-xs text-gray-600">
                            {c.websites - c.audited} not scanned
                        </div>
                    )}
                </>
            ),
        },
        {
            // Rule failures (a rule failing on one page counts once), as on the dashboard;
            // a website's own page counts elements.
            title: 'Critical + serious rule failures',
            key: 'cs',
            render: (_: unknown, c: Scorecard) => c.critical + c.serious,
        },
        {
            // What the counts leave out, beside them: owners can hide elements.
            title: 'Elements marked false positive or accepted',
            dataIndex: 'suppressed',
            key: 'suppressed',
            render: (v: number) => (v ? <Tag color="gold">{v}</Tag> : 0),
        },
        {
            title: 'Overdue',
            dataIndex: 'overdue',
            key: 'overdue',
            render: (v: number) => (v ? <Tag color="red">{v}</Tag> : 0),
        },
        {
            title: 'Websites with no critical or serious issues',
            dataIndex: 'clean_percent',
            key: 'clean',
            render: pct,
        },
        {
            title: 'Manually reviewed',
            dataIndex: 'reviewed_percent',
            key: 'reviewed',
            render: pct,
        },
        {
            title: 'Median days to fix',
            dataIndex: 'median_days_to_fix',
            key: 'fix',
            render: (v: number | null) => v ?? '—',
        },
        {
            title: 'Uptime (30 days)',
            key: 'uptime',
            render: (_: unknown, c: Scorecard) => (
                <>
                    {pct(c.uptime_30d)}
                    {c.down > 0 && (
                        <Tag color="red" className="ml-1">
                            {c.down} down
                        </Tag>
                    )}
                    {c.tls_problems > 0 && (
                        <Tag color="orange" className="ml-1">
                            {c.tls_problems} certificate
                        </Tag>
                    )}
                </>
            ),
        },
        {
            title: 'Upkeep',
            key: 'upkeep',
            render: (_: unknown, c: Scorecard) => (
                <span className="text-xs">
                    {c.stale_pages} stale pages · {c.mixed_content_pages} mixed content ·{' '}
                    {c.media_missing_captions} videos without captions
                </span>
            ),
        },
    ];

    return (
        <>
            <PageHeading
                title="Scorecards"
                subtitle="By department, over the websites you can see"
                actions={
                    <div className="flex gap-2">
                        <Button href={reportHref()}>Compliance report</Button>
                        <Button href="/api/compliance-report/?format=csv">Download CSV</Button>
                    </div>
                }
            />
            <Content className="p-6">
                {!data ? (
                    <PageLoading />
                ) : (
                    <>
                        <p style={{ marginBottom: 16 }} className="text-sm text-gray-600">
                            Set a website&apos;s department in its Settings tab. Retired websites
                            are left out.
                        </p>
                        <Table<Scorecard>
                            rowKey="department"
                            pagination={false}
                            scroll={{ x: true }}
                            dataSource={[
                                ...data.departments,
                                ...(data.totals ? [data.totals] : []),
                            ]}
                            columns={columns}
                            locale={{ emptyText: 'No websites yet.' }}
                        />
                    </>
                )}
            </Content>
        </>
    );
}

export default Scorecards;

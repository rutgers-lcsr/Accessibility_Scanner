'use client';
import PageError from '@/components/PageError';
import PageLoading from '@/components/PageLoading';
import { fetcherApi } from '@/lib/api';
import { HealthSummary } from '@/lib/types/health';
import { PublicUser } from '@/lib/types/user';
import { useAlerts } from '@/providers/Alerts';
import { useUser } from '@/providers/User';
import { Button, Descriptions, Empty, Table, Tag } from 'antd';
import { useState } from 'react';
import useSWR from 'swr';

type Props = {
    websiteId: number;
    user: PublicUser | null;
    canEdit: boolean;
};

// What each header protects against, for the table.
const HEADER_PURPOSE: Record<string, string> = {
    'Strict-Transport-Security': 'Browsers only ever connect over HTTPS.',
    'Content-Security-Policy': 'Limits where scripts and other content may load from.',
    'X-Content-Type-Options': 'Stops browsers guessing file types (should be nosniff).',
    'X-Frame-Options': 'Stops other sites framing this one (clickjacking).',
    'Referrer-Policy': 'Limits what the site leaks in the Referer header.',
    'Permissions-Policy': 'Turns off browser features the site does not use.',
};

const percent = (value: number | null) => (value === null ? '—' : `${value}%`);
const when = (value: string | null) => (value ? new Date(value).toLocaleString() : '—');

function Section({ title, children }: { title: string; children: React.ReactNode }) {
    return (
        <section className="mb-8" aria-label={title}>
            <h3 className="mb-3 text-lg font-semibold text-gray-800">{title}</h3>
            {children}
        </section>
    );
}

// The latest health check of a website: uptime, certificate, headers, platform and the
// content it must carry, with a strip of the recent checks.
function WebsiteHealth({ websiteId, user, canEdit }: Props) {
    const { handlerUserApiRequest } = useUser();
    const { addAlert } = useAlerts();
    const [checking, setChecking] = useState(false);
    const { data, error, mutate } = useSWR(
        `/api/websites/${websiteId}/health/`,
        user ? handlerUserApiRequest<HealthSummary> : fetcherApi<HealthSummary>
    );

    const checkNow = async () => {
        setChecking(true);
        try {
            const fresh = await handlerUserApiRequest<HealthSummary>(
                `/api/websites/${websiteId}/health/check/`,
                { method: 'POST' }
            );
            await mutate(fresh, { revalidate: false });
        } catch (e) {
            addAlert('Health check failed: ' + (e as Error).message, 'error');
        }
        setChecking(false);
    };

    if (error) return <PageError status={500} title="Error loading site health" />;
    if (!data) return <PageLoading minimal />;
    const { health, uptime, recent } = data;

    const action = canEdit && (
        <Button onClick={checkNow} loading={checking}>
            Check now
        </Button>
    );

    if (!health) {
        return (
            <div className="py-6">
                <Empty description="This website has not been checked yet. Checks run every few minutes.">
                    {action}
                </Empty>
            </div>
        );
    }

    const headerRows = data.security_headers.map((name) => ({
        name,
        value: health.security_headers[name] ?? null,
    }));

    return (
        <div className="py-4">
            <div className="mb-6 flex flex-wrap items-center gap-3">
                {health.up ? (
                    <Tag color="green" className="text-base">
                        Up
                    </Tag>
                ) : (
                    <Tag color="red" className="text-base">
                        Down
                    </Tag>
                )}
                <span className="text-sm text-gray-700">
                    {health.up ? 'Up' : 'Down'} since {when(health.up_changed_at)}
                    {health.response_ms !== null && <> · responded in {health.response_ms} ms</>}
                    {health.error && <> · {health.error}</>}
                </span>
                <span className="text-sm text-gray-500">
                    Last checked {when(health.checked_at)}
                </span>
                <span className="ml-auto">{action}</span>
            </div>

            <Section title="Uptime">
                <Descriptions
                    size="small"
                    bordered
                    column={{ xs: 1, sm: 3 }}
                    items={[
                        { key: 'day', label: 'Last 24 hours', children: percent(uptime.day) },
                        { key: 'week', label: 'Last 7 days', children: percent(uptime.week) },
                        { key: 'month', label: 'Last 30 days', children: percent(uptime.month) },
                    ]}
                />
                {recent.length > 0 && (
                    <div className="mt-3">
                        <div className="mb-1 text-xs text-gray-500">
                            Last {recent.length} checks, oldest first
                        </div>
                        <ol className="flex h-6 items-stretch gap-px" aria-label="Recent checks">
                            {recent.map((check) => (
                                <li
                                    key={check.checked_at}
                                    className={`w-2 rounded-sm ${check.up ? 'bg-green-600' : 'bg-red-600'}`}
                                    title={`${when(check.checked_at)}: ${check.up ? 'up' : 'down'}${check.error ? ` (${check.error})` : ''}`}
                                >
                                    <span className="sr-only">
                                        {when(check.checked_at)}: {check.up ? 'up' : 'down'}
                                    </span>
                                </li>
                            ))}
                        </ol>
                    </div>
                )}
            </Section>

            <Section title="HTTPS and certificate">
                <Descriptions
                    size="small"
                    bordered
                    column={1}
                    items={[
                        {
                            key: 'tls',
                            label: 'Certificate',
                            children:
                                health.tls_valid === true ? (
                                    <>
                                        <Tag color={health.tls_expiring ? 'orange' : 'green'}>
                                            {health.tls_expiring ? 'Expires soon' : 'Valid'}
                                        </Tag>
                                        expires {when(health.tls_expires_at)}
                                        {health.tls_days_left !== undefined && (
                                            <> ({health.tls_days_left} days)</>
                                        )}
                                        {health.tls_issuer && <>, issued by {health.tls_issuer}</>}
                                    </>
                                ) : health.tls_valid === false ? (
                                    <>
                                        <Tag color="red">Problem</Tag>
                                        {health.tls_error}
                                    </>
                                ) : (
                                    <span className="text-gray-500">
                                        Could not check: {health.tls_error}
                                    </span>
                                ),
                        },
                        {
                            key: 'redirect',
                            label: 'http:// redirects to https://',
                            children:
                                health.https_redirect === null ? (
                                    <span className="text-gray-500">Could not check</span>
                                ) : health.https_redirect ? (
                                    <Tag color="green">Yes</Tag>
                                ) : (
                                    <Tag color="orange">No</Tag>
                                ),
                        },
                    ]}
                />
            </Section>

            <Section title="Security headers">
                <Table
                    size="small"
                    pagination={false}
                    rowKey="name"
                    dataSource={headerRows}
                    columns={[
                        { title: 'Header', dataIndex: 'name', key: 'name' },
                        {
                            title: 'Sent',
                            dataIndex: 'value',
                            key: 'value',
                            render: (value: string | null) =>
                                value ? (
                                    <>
                                        <Tag color="green">Yes</Tag>
                                        <code className="text-xs break-all">{value}</code>
                                    </>
                                ) : (
                                    <Tag color="orange">Missing</Tag>
                                ),
                        },
                        {
                            title: 'What it does',
                            dataIndex: 'name',
                            key: 'purpose',
                            render: (name: string) => (
                                <span className="text-gray-600">{HEADER_PURPOSE[name]}</span>
                            ),
                        },
                    ]}
                />
            </Section>

            <Section title="Platform">
                <Descriptions
                    size="small"
                    bordered
                    column={1}
                    items={[
                        {
                            key: 'platform',
                            label: 'Runs on',
                            children: health.platform ? (
                                `${health.platform}${health.platform_version ? ` ${health.platform_version}` : ''}`
                            ) : (
                                <span className="text-gray-500">Not recognised</span>
                            ),
                        },
                        { key: 'server', label: 'Web server', children: health.server ?? '—' },
                    ]}
                />
            </Section>

            <Section title="Required content">
                {health.requirements.length === 0 ? (
                    <p className="text-sm text-gray-600">
                        No content requirements apply to this website. Site admins assign them under
                        Settings, Content requirements.
                    </p>
                ) : (
                    <ul className="space-y-2">
                        {health.requirements.map((result) => (
                            <li key={result.id} className="flex flex-wrap items-baseline gap-2">
                                {result.passed ? (
                                    <Tag color="green">Found</Tag>
                                ) : (
                                    <Tag color="red">Missing</Tag>
                                )}
                                <span className="font-medium">{result.name}</span>
                                {result.detail && (
                                    <span className="text-xs text-gray-500">{result.detail}</span>
                                )}
                            </li>
                        ))}
                    </ul>
                )}
            </Section>
        </div>
    );
}

export default WebsiteHealth;

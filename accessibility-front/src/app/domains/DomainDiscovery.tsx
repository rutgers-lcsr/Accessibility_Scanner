'use client';
import { Domain } from '@/lib/types/domain';
import { useAlerts } from '@/providers/Alerts';
import { useDomains } from '@/providers/Domain';
import { useUser } from '@/providers/User';
import { Alert, Button, Select, Switch, Table, Tag } from 'antd';
import Link from 'next/link';
import { useState } from 'react';
import useSWR from 'swr';

type DiscoveredHost = {
    id: number;
    host: string;
    sources: string[];
    status: 'new' | 'ignored' | 'tracked';
    website_id: number | null;
    note: string | null;
    first_seen: string;
    resolves: boolean | null;
    http_status: number | null;
    final_url: string | null;
    title: string | null;
    probe_error: string | null;
    checked_at: string | null;
};

type Listing = { domain: Domain; items: DiscoveredHost[] };
type Filter = 'new' | 'ignored' | 'tracked' | 'all';

const SOURCE_LABELS: Record<string, string> = {
    ct: 'certificates',
    links: 'linked from our sites',
};

// Hosts under one domain that may be websites nobody has added: from public certificate
// transparency logs and from what the crawled websites link to. Site admins add them as
// websites or ignore them.
function DomainDiscovery({ domainId }: { domainId: string }) {
    const { handlerUserApiRequest } = useUser();
    const { addAlert } = useAlerts();
    const { patchDomain } = useDomains();
    const [filter, setFilter] = useState<Filter>('new');
    const [waiting, setWaiting] = useState<string | null>(null);
    const [busy, setBusy] = useState<number | null>(null);
    const { data, mutate } = useSWR(
        `/api/domains/${domainId}/discovered/${filter === 'all' ? '' : `?status=${filter}`}`,
        handlerUserApiRequest<Listing>,
        // While a run is in the background, look again every 10 seconds until it lands.
        { refreshInterval: waiting !== null ? 10000 : 0 }
    );
    // ``waiting`` holds the last run's time when this one started; a new time means done.
    const lastRun = data ? (data.domain.discovered_at ?? 'never') : null;
    if (waiting !== null && lastRun !== null && lastRun !== waiting) setWaiting(null);

    const run = async () => {
        try {
            await handlerUserApiRequest(`/api/domains/${domainId}/discover/`, { method: 'POST' });
            setWaiting(lastRun ?? 'never');
            addAlert(
                'Discovery started. The list updates when it finishes, usually within a few minutes.',
                'info'
            );
        } catch (e) {
            addAlert('Could not start discovery: ' + (e as Error).message, 'error');
        }
    };

    const setStatus = async (row: DiscoveredHost, status: 'new' | 'ignored') => {
        setBusy(row.id);
        try {
            await handlerUserApiRequest(`/api/domains/discovered/${row.id}/`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status }),
            });
            await mutate();
        } catch (e) {
            addAlert('Could not save: ' + (e as Error).message, 'error');
        }
        setBusy(null);
    };

    const addWebsite = async (row: DiscoveredHost) => {
        setBusy(row.id);
        try {
            const website = await handlerUserApiRequest<{ id: number }>('/api/websites/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ base_url: row.final_url ?? `https://${row.host}` }),
            });
            addAlert(`Added ${row.host}`, 'success');
            await mutate();
            return website;
        } catch (e) {
            addAlert(`Could not add ${row.host}: ` + (e as Error).message, 'error');
        } finally {
            setBusy(null);
        }
    };

    const domain = data?.domain;

    return (
        <section
            aria-labelledby="discovery-heading"
            className="mt-8 rounded-lg bg-white p-4 shadow"
        >
            <h2 id="discovery-heading" className="mb-1 text-xl font-semibold">
                Find sites under {domain?.domain ?? '…'}
            </h2>
            <p className="mb-4 text-sm text-gray-600">
                Hosts named in public certificate transparency logs (looked up at crt.sh, which
                receives only the domain name) and hosts our crawled websites link to. Live ones are
                listed first.
            </p>
            {domain && (
                <div className="mb-4 flex flex-wrap items-center gap-4">
                    <Button type="primary" onClick={run} loading={waiting !== null}>
                        {waiting !== null ? 'Discovering…' : 'Run discovery now'}
                    </Button>
                    <span className="flex items-center gap-2">
                        <Switch
                            id="discovery-weekly"
                            checked={domain.discovery_enabled}
                            onChange={async (checked) => {
                                await patchDomain(domain.id, { discovery_enabled: checked });
                                mutate();
                            }}
                        />
                        <label htmlFor="discovery-weekly">Run every week</label>
                    </span>
                    <span className="text-sm text-gray-500">
                        Last run:{' '}
                        {domain.discovered_at
                            ? new Date(domain.discovered_at).toLocaleString()
                            : 'never'}
                    </span>
                    <span className="ml-auto flex items-center gap-2">
                        <label htmlFor="discovery-filter">Show</label>
                        <Select<Filter>
                            id="discovery-filter"
                            style={{ width: 200 }}
                            value={filter}
                            onChange={setFilter}
                            options={[
                                { value: 'new', label: 'Not tracked yet' },
                                { value: 'tracked', label: 'Already websites' },
                                { value: 'ignored', label: 'Ignored' },
                                { value: 'all', label: 'All' },
                            ]}
                        />
                    </span>
                </div>
            )}
            {domain?.discovery_error && (
                <Alert
                    className="mb-4"
                    type="warning"
                    showIcon
                    title="The certificate transparency lookup failed on the last run"
                    description={`${domain.discovery_error}. Hosts from our own crawls were still listed; try again later.`}
                />
            )}
            <Table<DiscoveredHost>
                rowKey="id"
                loading={!data}
                dataSource={data?.items ?? []}
                pagination={{ pageSize: 25, hideOnSinglePage: true }}
                locale={{
                    emptyText: domain?.discovered_at
                        ? 'Nothing here.'
                        : 'Run discovery to look for sites.',
                }}
                columns={[
                    {
                        title: 'Host',
                        dataIndex: 'host',
                        key: 'host',
                        render: (host: string, row) => (
                            <>
                                <a
                                    href={row.final_url ?? `https://${host}`}
                                    target="_blank"
                                    rel="noreferrer"
                                >
                                    {host}
                                </a>
                                {row.title && (
                                    <div className="text-xs text-gray-500">{row.title}</div>
                                )}
                            </>
                        ),
                    },
                    {
                        title: 'Answers',
                        key: 'live',
                        render: (_, row) =>
                            row.checked_at === null ? (
                                <span className="text-gray-500">Not checked</span>
                            ) : row.http_status ? (
                                <Tag color={row.http_status < 400 ? 'green' : 'orange'}>
                                    HTTP {row.http_status}
                                </Tag>
                            ) : row.resolves ? (
                                <Tag>No web server</Tag>
                            ) : (
                                <Tag>No DNS</Tag>
                            ),
                    },
                    {
                        title: 'Found in',
                        dataIndex: 'sources',
                        key: 'sources',
                        render: (sources: string[]) =>
                            sources.map((s) => SOURCE_LABELS[s] ?? s).join(', '),
                    },
                    {
                        title: '',
                        key: 'actions',
                        render: (_, row) =>
                            row.status === 'tracked' ? (
                                <Link href={`/websites/${row.website_id}`}>Open website</Link>
                            ) : (
                                <div className="flex flex-wrap gap-2">
                                    {row.status === 'new' && (
                                        <Button
                                            size="small"
                                            type="primary"
                                            disabled={!row.http_status || row.http_status >= 400}
                                            loading={busy === row.id}
                                            onClick={() => addWebsite(row)}
                                        >
                                            Add as website
                                        </Button>
                                    )}
                                    <Button
                                        size="small"
                                        loading={busy === row.id}
                                        onClick={() =>
                                            setStatus(
                                                row,
                                                row.status === 'ignored' ? 'new' : 'ignored'
                                            )
                                        }
                                    >
                                        {row.status === 'ignored' ? 'Restore' : 'Ignore'}
                                    </Button>
                                </div>
                            ),
                    },
                ]}
            />
        </section>
    );
}

export default DomainDiscovery;

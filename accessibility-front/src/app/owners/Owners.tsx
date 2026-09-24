'use client';
import PageError from '@/components/PageError';
import PageHeading from '@/components/PageHeading';
import PageLoading from '@/components/PageLoading';
import { Owner, OwnersResponse } from '@/lib/types/owners';
import { useAlerts } from '@/providers/Alerts';
import { useUser } from '@/providers/User';
import { DownloadOutlined, MailOutlined } from '@ant-design/icons';
import { Button, Input, Popconfirm } from 'antd';
import { Content } from 'antd/es/layout/layout';
import { Key, useState } from 'react';
import useSWR from 'swr';
import OwnersTable from './OwnersTable';

const matches = (owner: Owner, query: string) =>
    (owner.username ?? 'unassigned').toLowerCase().includes(query) ||
    (owner.email ?? '').toLowerCase().includes(query) ||
    owner.websites.some((site) => site.url.toLowerCase().includes(query));

const plural = (count: number, noun: string) => `${count} ${noun}${count === 1 ? '' : 's'}`;

function Owners() {
    const { handlerUserApiRequest } = useUser();
    const { addAlert } = useAlerts();
    const [search, setSearch] = useState('');
    const [selectedRowKeys, setSelectedRowKeys] = useState<Key[]>([]);
    const [progress, setProgress] = useState<{ done: number; total: number } | null>(null);

    const { data, error, isLoading, mutate } = useSWR(
        '/api/dashboard/owners',
        handlerUserApiRequest<OwnersResponse>
    );

    if (error) return <PageError status={500} title="Error loading owners" />;
    if (isLoading || !data) return <PageLoading />;

    const query = search.trim().toLowerCase();
    const owners = query ? data.owners.filter((owner) => matches(owner, query)) : data.owners;
    // Owner rows have string keys; only website rows (numeric ids) get emailed.
    const websiteIds = selectedRowKeys.filter((key): key is number => typeof key === 'number');
    const count = websiteIds.length;

    // One request per website: building a report email is slow, so a single request
    // for all of them would not fit the API's timeout.
    const sendEmails = async () => {
        let emailed = 0;
        let nobody = 0;
        let failed = 0;
        for (const [index, id] of websiteIds.entries()) {
            setProgress({ done: index, total: count });
            try {
                const result = await handlerUserApiRequest<{ sent: number }>(
                    `/api/websites/email/${id}`,
                    {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({}),
                    }
                );
                if (result.sent > 0) emailed += 1;
                else nobody += 1;
            } catch {
                failed += 1;
            }
        }
        setProgress(null);
        const parts = [`Digest sent for ${plural(emailed, 'website')}`];
        if (nobody) parts.push(`${nobody} had no one to email`);
        if (failed) parts.push(`${failed} failed`);
        addAlert(parts.join('; '), failed ? 'warning' : 'success');
        setSelectedRowKeys([]);
        mutate(); // last_notified and the "since last email" baseline moved
    };

    return (
        <>
            <PageHeading
                title="Owners"
                subtitle="Who owns each website and whether it is getting fixed"
            />
            <Content className="mb-8 p-4">
                <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                    <Input.Search
                        className="w-96"
                        placeholder="Search by owner, email or URL"
                        aria-label="Search by owner, email or URL"
                        allowClear
                        onSearch={(value) => {
                            setSearch(value);
                            setSelectedRowKeys([]);
                        }}
                    />
                    <div className="flex flex-wrap items-center gap-3">
                        <span className="text-sm text-gray-600" aria-live="polite">
                            {plural(count, 'website')} selected
                        </span>
                        <Popconfirm
                            title={`Send the digest for ${plural(count, 'website')}?`}
                            description="The admin and users of each website get its digest now: what to fix first and what changed."
                            okText="Send"
                            onConfirm={sendEmails}
                            disabled={count === 0 || progress !== null}
                        >
                            <Button
                                type="primary"
                                icon={<MailOutlined />}
                                disabled={count === 0}
                                loading={progress !== null}
                            >
                                {progress
                                    ? `Sending ${progress.done + 1} of ${progress.total}`
                                    : 'Send digest'}
                            </Button>
                        </Popconfirm>
                        <Button
                            icon={<DownloadOutlined />}
                            onClick={() =>
                                window.open('/api/dashboard/owners?format=csv', '_blank')
                            }
                        >
                            Export CSV
                        </Button>
                    </div>
                </div>
                <div className="rounded-lg bg-white p-4 shadow">
                    <OwnersTable
                        owners={owners}
                        periodDays={data.period.days}
                        selectedRowKeys={selectedRowKeys}
                        onSelectionChange={setSelectedRowKeys}
                    />
                </div>
            </Content>
        </>
    );
}

export default Owners;

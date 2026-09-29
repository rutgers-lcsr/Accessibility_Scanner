'use client';
import PageError from '@/components/PageError';
import PageLoading from '@/components/PageLoading';
import { LinkCell } from '@/components/LinkCell';
import { LinkStatusTag } from '@/components/LinkStatusTag';
import { fetcherApi } from '@/lib/api';
import { Paged } from '@/lib/types/Paged';
import { LinkSource, LinkStatus, WebsiteLink } from '@/lib/types/link';
import { PublicUser } from '@/lib/types/user';
import { useUser } from '@/providers/User';
import { Pagination, Popover, Select, Table, TableColumnType } from 'antd';
import React from 'react';
import useSWR from 'swr';

type Props = {
    websiteId: number;
    user: PublicUser | null;
};

const STATUS_OPTIONS: { value: LinkStatus | 'all'; label: string }[] = [
    { value: 'broken', label: 'Broken' },
    { value: 'error', label: 'Errors' },
    { value: 'blocked', label: 'Blocked' },
    { value: 'ok', label: 'Working' },
    { value: 'pending', label: 'Not checked yet' },
    { value: 'skipped', label: 'Skipped' },
    { value: 'all', label: 'All links' },
];

const SOURCES_SHOWN = 3;

// Where a link is on: page URL (to the page's report when it has one) and the link text
// there; the rest behind "more".
function SourcePage({ source }: { source: LinkSource }) {
    return (
        <div className="mb-1">
            <a href={source.report_id ? `/reports/${source.report_id}` : source.url} className="break-all">
                {source.url}
            </a>
            {source.text && <span className="ml-2 text-xs text-gray-500">“{source.text}”</span>}
        </div>
    );
}

function SourcePages({ sources }: { sources: LinkSource[] }) {
    const shown = sources.slice(0, SOURCES_SHOWN);
    const rest = sources.slice(SOURCES_SHOWN);
    return (
        <>
            {shown.map((source) => (
                <SourcePage key={source.url} source={source} />
            ))}
            {rest.length > 0 && (
                <Popover
                    content={
                        <div className="max-w-lg max-h-80 overflow-auto">
                            {rest.map((source) => (
                                <SourcePage key={source.url} source={source} />
                            ))}
                        </div>
                    }
                >
                    <button type="button" className="text-xs text-blue-700 hover:underline">
                        and {rest.length} more {rest.length === 1 ? 'page' : 'pages'}
                    </button>
                </Popover>
            )}
        </>
    );
}

// The links a website's pages carry, broken ones first, with the pages each is on.
function WebsiteLinksTable({ websiteId, user }: Props) {
    const { handlerUserApiRequest } = useUser();
    const [currentPage, setCurrentPage] = React.useState(1);
    const [pageSize, setPageSize] = React.useState(10);
    const [status, setStatus] = React.useState<LinkStatus | 'all'>('all');

    const query = `page=${currentPage}&limit=${pageSize}${status === 'all' ? '' : `&status=${status}`}`;
    const { data, error, isLoading } = useSWR(
        `/api/websites/${websiteId}/links?${query}`,
        user ? handlerUserApiRequest<Paged<WebsiteLink>> : fetcherApi<Paged<WebsiteLink>>
    );

    const columns: TableColumnType<WebsiteLink>[] = [
        {
            title: 'Link',
            dataIndex: 'url',
            key: 'url',
            width: 420,
            render: (url: string, record: { external: boolean; final_url: string | null }) => (
                <LinkCell url={url} external={record.external} final_url={record.final_url} />
            ),
        },
        {
            title: 'Status',
            dataIndex: 'status',
            key: 'status',
            render: (s: LinkStatus, record: WebsiteLink) => (
                <LinkStatusTag status={s} code={record.status_code} error={record.error} />
            ),
        },
        {
            title: 'Linked from',
            dataIndex: 'found_on',
            key: 'found_on',
            width: 420,
            render: (found: LinkSource[]) => <SourcePages sources={found} />,
        },
        {
            title: 'Last checked',
            dataIndex: 'checked_at',
            key: 'checked_at',
            render: (v: string | null) => (v ? new Date(v).toLocaleDateString() : ''),
        },
    ];

    if (error) return <PageError status={500} title="Error loading links" />;

    return (
        <>
            <div className="flex items-center gap-2" style={{ margin: '12px 0' }}>
                <label htmlFor="link-status-filter">Show</label>
                <Select
                    id="link-status-filter"
                    style={{ width: 180 }}
                    value={status}
                    options={STATUS_OPTIONS}
                    onChange={(value) => {
                        setStatus(value);
                        setCurrentPage(1);
                    }}
                />
            </div>
            {!data ? (
                <PageLoading minimal />
            ) : (
                <>
                    <Table<WebsiteLink>
                        style={{ width: '100%' }}
                        pagination={false}
                        columns={columns}
                        dataSource={data.items}
                        loading={isLoading}
                        rowKey="id"
                        locale={{
                            emptyText:
                                status === 'all' ? 'No links were found on this website.' : 'No links with this status.',
                        }}
                    />
                    <div className="flex justify-center pt-4 pb-4">
                        <Pagination
                            showSizeChanger
                            current={currentPage}
                            pageSize={pageSize}
                            total={data.count || 0}
                            onShowSizeChange={(current, newPageSize) => setPageSize(newPageSize)}
                            onChange={(page) => setCurrentPage(page)}
                        />
                    </div>
                </>
            )}
        </>
    );
}

export default WebsiteLinksTable;

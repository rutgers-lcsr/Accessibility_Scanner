'use client';
import PageError from '@/components/PageError';
import PageLoading from '@/components/PageLoading';
import { fetcherApi } from '@/lib/api';
import { PageContent, PageContentList } from '@/lib/types/inventory';
import { PublicUser } from '@/lib/types/user';
import { useUser } from '@/providers/User';
import { Pagination, Select, Table, Tag } from 'antd';
import React from 'react';
import useSWR from 'swr';

type Props = {
    websiteId: number;
    user: PublicUser | null;
};

type Filter = 'all' | 'stale' | 'mixed';

const day = (value: string | null) => (value ? new Date(value).toLocaleDateString() : '—');

// The website's pages by when their content last changed (oldest first), with any
// http:// resources an https:// page still loads.
function WebsiteContent({ websiteId, user }: Props) {
    const { handlerUserApiRequest } = useUser();
    const [page, setPage] = React.useState(1);
    const [pageSize, setPageSize] = React.useState(10);
    const [filter, setFilter] = React.useState<Filter>('all');
    const query = `page=${page}&limit=${pageSize}${filter === 'all' ? '' : `&filter=${filter}`}`;
    const { data, error, isLoading } = useSWR(
        `/api/websites/${websiteId}/content/?${query}`,
        user ? handlerUserApiRequest<PageContentList> : fetcherApi<PageContentList>
    );
    if (error) return <PageError status={500} title="Error loading page content" />;

    return (
        <>
            <p style={{ marginTop: 8, marginBottom: 16 }} className="text-sm text-gray-600">
                A page is stale when its main text has not changed in{' '}
                {data ? `${data.stale_after_days} days` : 'a long time'}. The date is the
                server&apos;s Last-Modified header when it sends one, otherwise the first scan that
                saw the current text, so a page first scanned recently can look fresher than it is.
                Stale pages are good candidates for an update or for retiring.
            </p>
            <div className="mb-3 flex items-center gap-2">
                <label htmlFor="content-filter">Show</label>
                <Select<Filter>
                    id="content-filter"
                    style={{ width: 220 }}
                    value={filter}
                    onChange={(value) => {
                        setFilter(value);
                        setPage(1);
                    }}
                    options={[
                        { value: 'all', label: 'All pages' },
                        { value: 'stale', label: 'Stale pages' },
                        { value: 'mixed', label: 'Pages with mixed content' },
                    ]}
                />
            </div>
            {!data ? (
                <PageLoading minimal />
            ) : (
                <>
                    <Table<PageContent>
                        rowKey="site_id"
                        loading={isLoading}
                        pagination={false}
                        dataSource={data.items}
                        locale={{ emptyText: 'No pages match.' }}
                        columns={[
                            {
                                title: 'Page',
                                dataIndex: 'url',
                                key: 'url',
                                width: 420,
                                render: (url: string, row) => (
                                    <a
                                        href={row.report_id ? `/reports/${row.report_id}` : url}
                                        className="break-all"
                                    >
                                        {url}
                                    </a>
                                ),
                            },
                            {
                                title: 'Content last changed',
                                dataIndex: 'content_changed_at',
                                key: 'changed',
                                render: (value: string | null, row) => (
                                    <>
                                        {day(value)} {row.stale && <Tag color="orange">Stale</Tag>}
                                    </>
                                ),
                            },
                            {
                                title: 'Mixed content',
                                dataIndex: 'mixed_content',
                                key: 'mixed',
                                width: 360,
                                render: (mixed: PageContent['mixed_content']) =>
                                    mixed.length === 0 ? (
                                        <span className="text-gray-600">None</span>
                                    ) : (
                                        <>
                                            <Tag color="red">
                                                {mixed.length} http:// resource
                                                {mixed.length === 1 ? '' : 's'}
                                            </Tag>
                                            {mixed.slice(0, 3).map((item) => (
                                                <div
                                                    key={item.url + item.tag}
                                                    className="text-xs break-all"
                                                >
                                                    &lt;{item.tag}&gt; {item.url}
                                                </div>
                                            ))}
                                        </>
                                    ),
                            },
                        ]}
                    />
                    <div className="flex justify-center py-4">
                        <Pagination
                            showSizeChanger
                            current={page}
                            pageSize={pageSize}
                            total={data.count}
                            onShowSizeChange={(_, size) => setPageSize(size)}
                            onChange={setPage}
                        />
                    </div>
                </>
            )}
        </>
    );
}

export default WebsiteContent;

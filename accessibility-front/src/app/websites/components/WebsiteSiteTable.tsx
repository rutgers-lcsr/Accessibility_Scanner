import PageError from '@/components/PageError';
import PageLoading from '@/components/PageLoading';
import { fetcherApi } from '@/lib/api';
import { Paged } from '@/lib/types/Paged';
import { PublicUser } from '@/lib/types/user';
import { Site } from '@/lib/types/website';
import { useUser } from '@/providers/User';
import { Pagination, Table, Tag, Tooltip } from 'antd';
import { format } from 'date-fns';
import React from 'react';
import useSWR from 'swr';
import SiteHistoryChart from './SiteHistoryChart';

type Props = {
    websiteId: number;
    user: PublicUser | null;
};

function WebsiteSiteTable({ websiteId, user }: Props) {
    const { handlerUserApiRequest } = useUser();

    // Use a ref to avoid resetting pageSize on re-render
    const [currentPage, setCurrentPage] = React.useState(1);
    const [pageSize, setPageSize] = React.useState(10);

    const {
        data: sites,
        error: siteError,
        isLoading: isLoadingSites,
    } = useSWR(
        `/api/websites/${websiteId}/sites?page=${currentPage}&limit=${pageSize}`,
        user ? handlerUserApiRequest<Paged<Site>> : fetcherApi<Paged<Site>>
    );

    const sites_columns = [
        {
            title: 'URL',
            width: 300,
            dataIndex: 'url',
            key: 'url',
            render: (text: string, record: Site) =>
                record.current_report ? (
                    <a href={`/reports/${record.current_report.id}`}>{text}</a>
                ) : (
                    <span>{text}</span>
                ),
        },
        {
            title: 'Last Scanned',
            dataIndex: 'last_scanned',
            key: 'last_scanned',
            render: (date: string) => {
                if (!date) return 'Never';
                return format(new Date(date), 'MMMM dd, yyyy');
            },
        },
        {
            title: 'Passed',
            key: 'passed',
            render: (text: string, record: Site) => (
                <span>{record.current_report?.report_counts.passes.total ?? '—'}</span>
            ),
            dataIndex: 'passed',
        },
        {
            title: 'Violations',
            key: 'violations',
            render: (text: string, record: Site) => (
                <span>{record.current_report?.report_counts.violations.total ?? '—'}</span>
            ),
            dataIndex: 'violations',
        },
        {
            title: 'Active Tags',
            key: 'tags',
            render: (text: string, record: Site) => (
                <>
                    {record.tags.map((tag) => (
                        <Tag key={tag}>{tag}</Tag>
                    ))}
                </>
            ),
            onFilter: (value: boolean | React.Key, record: Site) =>
                record.tags.includes(value as string),
            dataIndex: 'tags',
        },
        {
            title: 'Last Scan',
            key: 'last_scan_status',
            dataIndex: 'last_scan_status',
            render: (status: Site['last_scan_status'], record: Site) => {
                if (status === 'failed') {
                    return (
                        <Tooltip title={record.last_scan_error || 'Unknown error'}>
                            <Tag color="red">Failed</Tag>
                        </Tooltip>
                    );
                }
                if (status === 'completed') {
                    return <Tag color="green">OK</Tag>;
                }
                return <Tag>Not yet scanned</Tag>;
            },
        },
        {
            title: 'Actions',
            key: 'actions',
            render: (text: string, record: Site) =>
                record.current_report ? (
                    <a href={`/reports/${record.current_report.id}`}>View Report</a>
                ) : (
                    <span className="text-gray-400">No report yet</span>
                ),
        },
    ];

    if (siteError) return <PageError status={500} title="Error loading sites" />;
    if (!sites) return <PageLoading minimal />;

    return (
        <>
            <Table<Site>
                className="min-h-[400px]"
                style={{ width: '100%', minHeight: 400, maxWidth: '100%' }}
                scroll={{ y: '45em' }}
                pagination={false}
                columns={sites_columns}
                dataSource={sites?.items}
                loading={isLoadingSites}
                rowKey="id"
                expandable={{
                    // SiteHistoryChart is only rendered for expanded rows, so each
                    // URL's history is fetched lazily on expand.
                    expandedRowRender: (record) => (
                        <SiteHistoryChart siteId={record.id} user={user} />
                    ),
                }}
            />

            <div className="flex justify-center pt-4 pb-4">
                <Pagination
                    showSizeChanger
                    current={currentPage}
                    pageSize={pageSize}
                    total={sites?.count || 0}
                    onShowSizeChange={(current, newPageSize) => {
                        setPageSize(newPageSize);
                    }}
                    onChange={(page) => setCurrentPage(page)}
                />
            </div>
        </>
    );
}

export default WebsiteSiteTable;

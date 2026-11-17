import PageError from '@/components/PageError';
import PageLoading from '@/components/PageLoading';
import RescanPageButton from '@/components/RescanPageButton';
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
    canScan?: boolean;
    onPageScanned?: () => void;
};

function WebsiteSiteTable({ websiteId, user, canScan = false, onPageScanned }: Props) {
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
            title: 'Page',
            width: 320,
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
            title: 'Last scanned',
            width: 180,
            dataIndex: 'last_scanned',
            key: 'last_scanned',
            render: (date: string) => {
                if (!date) return 'Never';
                return format(new Date(date), 'MMMM dd, yyyy');
            },
        },
        {
            // Rules, not elements: the same unit as the website's severity tiles.
            title: 'Failing rules',
            width: 90,
            key: 'violations',
            render: (text: string, record: Site) => (
                <span className="tabular-nums">
                    {/* A redirected page's counts are another site's: none here. */}
                    {record.current_report?.scanned_host
                        ? '—'
                        : (record.current_report?.report_counts.violations.total ?? '—')}
                </span>
            ),
            dataIndex: 'violations',
        },
        {
            title: 'Passing rules',
            width: 90,
            key: 'passed',
            render: (text: string, record: Site) => (
                <span className="tabular-nums">
                    {record.current_report?.scanned_host
                        ? '—'
                        : (record.current_report?.report_counts.passes.total ?? '—')}
                </span>
            ),
            dataIndex: 'passed',
        },
        {
            title: 'Last scan',
            width: 180,
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
                const elsewhere = record.current_report?.scanned_host;
                if (status === 'completed' && elsewhere) {
                    // Its results are another site's, so they count nothing here.
                    return (
                        <Tooltip
                            title={`When scanned, this page redirected to ${elsewhere}. Those results are not counted for this website.`}
                        >
                            <Tag color="gold">Scanned {elsewhere}</Tag>
                        </Tooltip>
                    );
                }
                // "OK" said the scan ran; next to a 50-day-old date it read as "page is fine".
                const stale =
                    !!record.last_scanned &&
                    Date.now() - new Date(record.last_scanned).getTime() > 30 * 86_400_000;
                if (status === 'completed' && stale) {
                    return <Tag color="gold">Stale (over 30 days)</Tag>;
                }
                if (status === 'completed') {
                    return <Tag color="green">Scanned</Tag>;
                }
                return <Tag>Not yet scanned</Tag>;
            },
        },
        ...(canScan
            ? [
                  {
                      title: <span className="sr-only">Actions</span>,
                      key: 'actions',
                      width: 150,
                      render: (text: string, record: Site) => (
                          <RescanPageButton
                              siteId={record.id}
                              pageUrl={record.url}
                              size="small"
                              onScanned={onPageScanned}
                          />
                      ),
                  },
              ]
            : []),
    ];

    if (siteError) return <PageError status={500} title="Error loading sites" />;
    if (!sites) return <PageLoading minimal />;

    return (
        <>
            <p className="mt-2 mb-4 text-sm text-gray-700">
                Pages with the most failing rules first. Open a page for its report; expand a row
                for its history.
            </p>
            <Table<Site>
                className="min-h-[400px]"
                style={{ width: '100%', minHeight: 400, maxWidth: '100%' }}
                // x: the sum of the column widths. Narrower screens scroll the table sideways
                // instead of crushing dates to one letter per line.
                scroll={{ x: 1060, y: '45em' }}
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

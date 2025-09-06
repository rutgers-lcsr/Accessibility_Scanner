"use client"
import HeaderLink from '@/app/reports/[reportId]/components/HeaderLink';
import { fetcherApi } from '@/lib/api';
import { Paged } from '@/lib/types/Paged';
import { User } from '@/lib/types/user';
import { Site, Website as WebsiteType } from '@/lib/types/website';
import { useUser } from '@/providers/User';
import {
    AlertOutlined,
    ExclamationCircleOutlined,
    InfoCircleOutlined,
    WarningOutlined,
} from '@ant-design/icons';
import { Pagination, Space, Table } from 'antd';
import { format } from 'date-fns';
import React from 'react';
import useSWR from 'swr';
import AdminWebsiteItems from './AdminWebsiteItems';
import PageError from './PageError';
import PageLoading from './PageLoading';

type Props = {
    websiteId: number;
    user: User | null;
};

const Website = ({ websiteId, user }: Props) => {
    const {  handlerUserApiRequest } = useUser();

    const {
        data: websiteReport,
        error: reportError,
        mutate: mutateWebsiteReport,
    } = useSWR(
        `/api/websites/${websiteId}`,
        user ? handlerUserApiRequest<WebsiteType> : fetcherApi<WebsiteType>
    );
    // Use a ref to avoid resetting pageSize on re-render
    const [currentPage, setCurrentPage] = React.useState(1);
    const [pageSize, setPageSize] = React.useState(10);
    React.useEffect(() => {
        setPageSize(pageSize);
    }, [pageSize]);

    const {
        data: sites,
        error: siteError,
        isLoading: isLoadingSites,
        mutate: mutateSites,
    } = useSWR(
        `/api/websites/${websiteId}/sites?page=${currentPage}&limit=${pageSize}`,
        user ? handlerUserApiRequest<Paged<Site>> : fetcherApi<Paged<Site>>
    );

    if (reportError) return <PageError status={500} title="Error loading website report" />;
    if (siteError) return <PageError status={500} title="Error loading sites" />;
    if (!websiteReport) return <PageLoading />;

    const violations = websiteReport.report_counts.violations;

    // Mutate both the website report and the sites data when it become stale,
    // this is needed for a full page reload when the website is scanned
    const mutate = async (website?: WebsiteType) => {
        mutateSites();
        mutateWebsiteReport(website);
    };

    const sites_columns = [
        {
            title: 'URL',
            width: 300,
            dataIndex: 'url',
            key: 'url',
            render: (text: string, record: Site) => (
                <a href={`/reports/${record.current_report.id}`}>{text}</a>
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
            title: 'Violations',
            key: 'violations',
            render: (text: string, record: Site) => (
                <span>{record.current_report.report_counts.violations.total}</span>
            ),
            onFilter: (value: boolean | React.Key, record: Site) =>
                record.current_report.report_counts.violations.total === Number(value),
            sorter: (a: Site, b: Site) =>
                a.current_report.report_counts.violations.total -
                b.current_report.report_counts.violations.total,
            dataIndex: 'violations',
        },
        {
            title: 'Actions',
            key: 'actions',
            render: (text: string, record: Site) => (
                <a href={`/reports/${record.current_report.id}`}>View Report</a>
            ),
        },
    ];


    return (
        <div>
            <header className="mb-8">
                <h1 className="mb-2 text-3xl font-extrabold">
                    Website Report for{' '}
                    <HeaderLink url={`https://${websiteReport.url}`} />
                </h1>
                {user && user.is_admin && <AdminWebsiteItems website={websiteReport} mutate={mutate} />}
                <h2 className="mb-4 text-lg text-gray-500">
                    Last Scanned:{' '}
                    {websiteReport?.last_scanned
                        ? format(websiteReport?.last_scanned, 'MMMM dd, yyyy')
                        : 'Never'}
                </h2>
                <section
                    role="region"
                    aria-labelledby="accessibility-report"
                    className="rounded-lg bg-gray-50 p-6"
                >
                    <h2
                        id="accessibility-report"
                        className="mb-6 text-2xl font-semibold text-gray-800"
                    >
                        Accessibility Report
                    </h2>
                    <div className="grid grid-cols-2 gap-6 text-center md:grid-cols-4">
                        <div className="flex flex-col items-center rounded-lg bg-red-50 p-4 shadow-sm">
                            <ExclamationCircleOutlined className="mb-2 text-3xl text-red-700" />
                            <h3 className="mb-2 text-lg font-medium text-red-700">Critical</h3>
                            <p className="text-3xl font-bold text-red-600">{violations.critical}</p>
                        </div>
                        <div className="flex flex-col items-center rounded-lg bg-red-100 p-4 shadow-sm">
                            <AlertOutlined className="mb-2 text-3xl text-red-700" />
                            <h3 className="mb-2 text-lg font-medium text-red-700">Serious</h3>
                            <p className="text-3xl font-bold text-red-600">{violations.serious}</p>
                        </div>
                        <div className="flex flex-col items-center rounded-lg bg-orange-50 p-4 shadow-sm">
                            <WarningOutlined className="mb-2 text-3xl text-orange-700" />
                            <h3 className="mb-2 text-lg font-medium text-orange-700">Moderate</h3>
                            <p className="text-3xl font-bold text-orange-600">
                                {violations.moderate}
                            </p>
                        </div>
                        <div className="flex flex-col items-center rounded-lg bg-yellow-50 p-4 shadow-sm">
                            <InfoCircleOutlined className="mb-2 text-3xl text-yellow-700" />
                            <h3 className="mb-2 text-lg font-medium text-yellow-700">Minor</h3>
                            <p className="text-3xl font-bold text-yellow-600">{violations.minor}</p>
                        </div>
                    </div>
                </section>
            </header>

            <Space
                direction="vertical"
                role="region"
                aria-labelledby="website-sites"
                className="rounded-lg bg-gray-50"
            >
                <Table<Site>
                    className="min-h-[400px]"
                    style={{ width: '100%', minHeight: 400, maxWidth: '100%' }}
                    scroll={{ y: '45em' }}
                    pagination={false}
                    columns={sites_columns}
                    dataSource={sites?.items}
                    loading={isLoadingSites}
                    rowKey="id"
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
            </Space>
        </div>
    );
};

export default Website;

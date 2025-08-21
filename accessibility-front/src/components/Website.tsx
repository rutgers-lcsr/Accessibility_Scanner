import { fetcherApi } from '@/lib/api';
import { Paged } from '@/lib/types/Paged';
import { Site, Website as WebsiteType } from '@/lib/types/website';
import React from 'react'
import useSWR from 'swr'
import { Pagination, Table } from 'antd';
import PageLoading from './PageLoading';
import {
    ExclamationCircleOutlined,
    WarningOutlined,
    InfoCircleOutlined,
    AlertOutlined,
} from '@ant-design/icons';

type Props = {
    websiteId: number;
}

const Website = ({ websiteId }: Props) => {



    const { data: websiteReport, error: reportError } = useSWR(`/api/websites/${websiteId}`, fetcherApi<WebsiteType>);
    // Use a ref to avoid resetting pageSize on re-render
    const [currentPage, setCurrentPage] = React.useState(1);
    const [pageSize, setPageSize] = React.useState(10);
    React.useEffect(() => {
        setPageSize(pageSize);
    }, [pageSize]);

    const { data: sites, error: siteError, isLoading: siteLoading } = useSWR(
        `/api/websites/${websiteId}/sites?page=${currentPage}&limit=${pageSize}`,
        fetcherApi<Paged<Site>>
    );

    if (reportError) return <div>Error loading website report</div>;
    if (siteError) return <div>Error loading website sites</div>;
    if (!sites) return <PageLoading />;
    if (!websiteReport) return <PageLoading />;

    const violations = websiteReport.report_counts.violations;

    const sites_columns = [
        {
            title: 'URL',
            dataIndex: 'url',
            key: 'url',
            render: (text: string, record: Site) => (
                <a href={`/reports?id=${record.current_report.id}`}>{text}</a>
            ),
        },
        {
            title: 'Last Scanned',
            dataIndex: 'last_scanned',
            key: 'last_scanned',
            render: (date: string) => new Date(date).toLocaleDateString(),
        },
        {
            title: 'Violations',
            key: 'violations',
            render: (text: string, record: Site) => (
                <span>{record.current_report.report_counts.violations.total}</span>
            ),
            onFilter: (value: boolean | React.Key, record: Site) =>
                record.current_report.report_counts.violations.total === Number(value),
            sorter: (a: Site, b: Site) => a.current_report.report_counts.violations.total - b.current_report.report_counts.violations.total,
            dataIndex: 'violations',
        },
        {
            title: 'Actions',
            key: 'actions',
            render: (text: string, record: Site) => (
                <a href={`/reports?id=${record.current_report.id}`}>View Report</a>
            ),
        },
    ];

    return (
        <div className="max-w-4xl mx-auto ">
            <header className="mb-8">
                <h1 className="text-3xl font-extrabold mb-2">
                    Website Report for <span onClick={() => window.open(websiteReport.base_url,)} className="underline text-blue-700">{websiteReport.base_url}</span>
                </h1>
                <h2 className="text-gray-500 text-lg mb-4">
                    Last Scanned: {websiteReport?.last_scanned}
                </h2>
                <section
                    role="region"
                    aria-labelledby="accessibility-report"
                    className="bg-gray-50 rounded-lg p-6"
                >
                    <h2 id="accessibility-report" className="text-2xl font-semibold mb-6 text-gray-800">
                        Accessibility Report
                    </h2>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
                        <div className="bg-red-50 rounded-lg p-4 shadow-sm flex flex-col items-center">
                            <ExclamationCircleOutlined className="text-3xl text-red-700 mb-2" />
                            <h3 className="text-lg font-medium text-red-700 mb-2">Critical</h3>
                            <p className="text-3xl font-bold text-red-600">{violations.critical}</p>
                        </div>
                        <div className="bg-red-100 rounded-lg p-4 shadow-sm flex flex-col items-center">
                            <AlertOutlined className="text-3xl text-red-700 mb-2" />
                            <h3 className="text-lg font-medium text-red-700 mb-2">Serious</h3>
                            <p className="text-3xl font-bold text-red-600">{violations.serious}</p>
                        </div>
                        <div className="bg-orange-50 rounded-lg p-4 shadow-sm flex flex-col items-center">
                            <WarningOutlined className="text-3xl text-orange-700 mb-2" />
                            <h3 className="text-lg font-medium text-orange-700 mb-2">Moderate</h3>
                            <p className="text-3xl font-bold text-orange-600">{violations.moderate}</p>
                        </div>
                        <div className="bg-yellow-50 rounded-lg p-4 shadow-sm flex flex-col items-center">
                            <InfoCircleOutlined className="text-3xl text-yellow-700 mb-2" />
                            <h3 className="text-lg font-medium text-yellow-700 mb-2">Minor</h3>
                            <p className="text-3xl font-bold text-yellow-600">{violations.minor}</p>
                        </div>
                    </div>
                </section>
            </header>

            <section
                role='region'
                aria-labelledby="website-sites"
                className='bg-gray-50 rounded-lg mt-8'
            >
                <Table<Site>
                    pagination={false}
                    columns={sites_columns}
                    dataSource={sites?.items}
                    loading={!sites}
                    rowKey="id"
                />

                <div className='justify-center flex pt-4 pb-4'>
                    <Pagination
                        showSizeChanger
                        current={currentPage}
                        pageSize={pageSize}
                        total={sites.count || 0}
                        onShowSizeChange={(current, newPageSize) => {
                            setPageSize(newPageSize);
                        }}
                        onChange={(page) => setCurrentPage(page)}
                    />
                </div>
            </section>
        </div>
    );

};



export default Website
'use client';
import PageError from '@/components/PageError';
import { Report as ReportType } from '@/lib/types/axe';
import { useReports } from '@/providers/Reports';
import { Flex, Input, Pagination, Table } from 'antd';
import { Content } from 'antd/es/layout/layout';
import { format } from 'date-fns';
const columns = [
    {
        title: 'Url',
        dataIndex: 'url',
        key: 'url',
        render: (text: string, record: ReportType) => <a href={`/reports/${record.id}`}>{text}</a>,
    },
    {
        title: 'Timestamp',
        dataIndex: 'timestamp',
        key: 'Timestamp',
        render: (text: string, record: ReportType) => (
            <span>{format(record.timestamp, 'MMMM dd, yyyy')}</span>
        ),
    },
    {
        title: 'Passed',
        dataIndex: 'passed',
        key: 'passed',
        render: (text: string, record: ReportType) => (
            <span>{record.report_counts.passes.total}</span>
        ),
    },
    {
        title: 'Violations',
        dataIndex: 'violations',
        key: 'violations',
        render: (text: string, record: ReportType) => (
            <span>{record.report_counts.violations.total}</span>
        ),
    },
];

export default function ReportPage() {
    const {
        reports,
        isLoading,
        setReportSearch,
        setReportPage,
        setReportLimit,
        reportsTotal,
        ReportPage,
    } = useReports();

    return (
        <Content className="p-6">
            <header className="mb-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                <h1 className="text-3xl font-bold text-gray-800">Accessibility Reports</h1>
                <div>
                    <Input.Search
                        className="w-64"
                        placeholder="Search reports"
                        onSearch={(value) => {
                            // console.log(value);
                            setReportSearch(value);
                        }}
                        loading={isLoading}
                        size="large"
                        allowClear
                    />
                </div>
            </header>
            <Content>
                <Table<ReportType>
                    rowKey="id"
                    columns={columns}
                    dataSource={reports || []}
                    loading={isLoading}
                    pagination={false}
                    bordered
                    size="middle"
                    className="bg-white rounded-lg"
                    locale={{
                        emptyText: (
                            <PageError
                                status={'info'}
                                title="No Reports Found"
                                subTitle="It seems we couldn't find any reports."
                            />
                        ),
                    }}
                />
                <Flex style={{ padding: '16px 0' }} justify="center">
                    <Pagination
                        showSizeChanger
                        defaultCurrent={ReportPage}
                        total={reportsTotal}
                        onShowSizeChange={(current, pageSize) => {
                            setReportLimit(pageSize);
                        }}
                        onChange={(current) => setReportPage(current)}
                    />
                </Flex>
            </Content>
        </Content>
    );
}

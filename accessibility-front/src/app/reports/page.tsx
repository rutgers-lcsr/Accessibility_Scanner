'use client';
import PageError from '@/components/PageError';
import PageHeading from '@/components/PageHeading';
import { PageSize, pageSizeOptions } from '@/lib/browser';
import { Report as ReportType } from '@/lib/types/axe';
import { useReports } from '@/providers/Reports';
import { Flex, Input, Pagination, Table } from 'antd';
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
        ReportLimit,
        setReportLimit,
        reportsTotal,
        ReportPage,
    } = useReports();

    return (
        <>
            <PageHeading
                title="Accessibility Reports"
                subtitle="Individual accessibility reports."
            />
            <div className="p-6">
                <Flex
                    className="mb-4"
                    justify="end"
                    align="flex-end"
                    gap="small"
                    style={{ minWidth: '300px', marginBottom: '16px' }}
                >
                    <Flex gap="middle" align="center">
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
                            aria-label="Search reports"
                        />
                    </Flex>
                </Flex>
                <div className="bg-white p-4 rounded-lg shadow">
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
                            pageSize={ReportLimit}
                            pageSizeOptions={pageSizeOptions}
                            onShowSizeChange={(current, pageSize) => {
                                setReportLimit(pageSize as PageSize);
                            }}
                            onChange={(current) => setReportPage(current)}
                        />
                    </Flex>
                </div>
            </div>
        </>
    );
}

'use client';
import PageError from '@/components/PageError';
import { Report as ReportType } from '@/lib/types/axe';
import { useReports } from '@/providers/Reports';
import { Input, Pagination, Table } from 'antd';
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
    // const searchParams = useSearchParams();
    const {
        reports,
        isLoading,
        setReportSearch,
        setReportPage,
        setReportLimit,
        reportsTotal,
        ReportPage,
    } = useReports();
    // const id = searchParams.get('id');

    // if (id) {
    //   return <Report report_id={id} />;
    // }

    return (
        <div className="">
            <header className="mb-4 flex w-full justify-between">
                <h1 className="text-2xl font-bold">Accessibility Reports</h1>
                <div>
                    <Input.Search
                        className="w-64"
                        placeholder="Search reports"
                        onSearch={(value) => {
                            // console.log(value);
                            setReportSearch(value);
                        }}
                        loading={isLoading}
                    />
                </div>
            </header>
            <main className="h-[calc(100vh-13rem)] overflow-y-auto">
                <Table<ReportType>
                    rowKey="id"
                    columns={columns}
                    dataSource={reports || []}
                    loading={isLoading}
                    pagination={false}
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
            </main>
            <footer className="mt-4 flex justify-center">
                <Pagination
                    showSizeChanger
                    defaultCurrent={ReportPage}
                    total={reportsTotal}
                    onShowSizeChange={(current, pageSize) => {
                        setReportLimit(pageSize);
                    }}
                    onChange={(current) => setReportPage(current)}
                />
            </footer>
        </div>
    );
}

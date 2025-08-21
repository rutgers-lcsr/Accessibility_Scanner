'use client';
import React from 'react';
import { Input, Table, Pagination } from 'antd';
import { useReports } from '@/providers/Reports';
import { Report as ReportType } from '@/lib/types/axe';
import { useSearchParams } from 'next/navigation';
import Report from '@/components/Report';


const columns = [
    {
        title: 'Url',
        dataIndex: 'url',
        key: 'url',
        render: (text: string, record: ReportType) => (
            <a href={`/reports?id=${record.id}`}>{text}</a>
        ),
    },
    {
        title: 'Timestamp',
        dataIndex: 'timestamp',
        key: 'Timestamp',
        render: (text: string, record: ReportType) => (
            <span>{new Date(record.timestamp).toLocaleDateString()}</span>
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
    }
];

export default function ReportPage() {
    const searchParams = useSearchParams()
    const {
        reports,
        isLoading,
        setReportSearch,
        setReportPage,
        setReportLimit,
        reportsTotal,
        ReportPage,

    } = useReports();
    const id = searchParams.get('id');

    if (id) {
        return <Report report_id={id} />
    }




    return <div className=''>
        <header className='flex mb-4 w-full justify-between'>
            <h1 className='text-2xl font-bold'>Reports</h1>
            <div>
                <Input.Search className='w-64' placeholder="Search reports" onSearch={(value) => {
                    console.log(value);
                    setReportSearch(value);
                }} loading={isLoading} />

            </div>
        </header>
        <main className='h-[calc(100vh-12rem)] overflow-y-auto'>


            <Table<ReportType>
                rowKey="id"
                columns={columns}
                dataSource={reports || []}
                loading={isLoading}
                pagination={false}
                locale={{ emptyText: 'No websites found.' }}
            />
        </main>
        <footer className="mt-4 justify-center flex">
            <Pagination showSizeChanger defaultCurrent={ReportPage} total={reportsTotal} onShowSizeChange={(current, pageSize) => {
                setReportLimit(pageSize);
            }} onChange={(current) => setReportPage(current)} />
        </footer>
    </div>;
}
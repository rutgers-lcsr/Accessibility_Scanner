"use client"
import { useWebsites } from '@/providers/Websites';
import Pagination from 'antd/es/pagination/Pagination';
import { Input } from 'antd';
import { useSearchParams } from 'next/navigation';
import Website from '@/components/Website';
import type { Website as WebsiteType } from '@/lib/types/website';
import { Table } from 'antd';

const columns = [
    {
        title: 'URL',
        dataIndex: 'base_url',
        key: 'base_url',
        render: (text: string, record: WebsiteType) => (
            <a href={`/websites?id=${record.id}`}>{text}</a>
        ),
    },
    {
        title: 'Last Scanned',
        dataIndex: 'last_scanned',
        key: 'last_scanned',
        render: (date: string) => new Date(date).toLocaleDateString(),
    },
    {
        title: 'Passes',
        dataIndex: 'passes',
        key: 'passes',
        render: (text: string, record: WebsiteType) => (
            <span>{record.report_counts.passes.total}</span>
        ),
    },
    {
        title: 'Violations',
        dataIndex: 'violations',
        key: 'violations',
        render: (text: string, record: WebsiteType) => (
            <span>{record.report_counts.violations.total}</span>
        ),
        sorter: (a: WebsiteType, b: WebsiteType) => a.report_counts.violations.total - b.report_counts.violations.total,
    },
    {
        title: 'Active',
        dataIndex: 'active',
        key: 'active',
        render: (active: boolean) => (active ? 'Yes' : 'No'),
    },
];


export default function Page() {
    const searchParams = useSearchParams();
    const {
        websites,
        websitesTotal,
        setWebsitePage,
        setWebsiteLimit,
        WebsitePage,
        isLoading,
        setWebsiteSearch
    } = useWebsites();
    const id = searchParams.get('id');

    if (id) {
        return <Website websiteId={Number(id)} />;
    }







    return <div className=''>
        <header className='flex mb-4 w-full justify-between'>
            <h1 className='text-2xl font-bold'>Websites</h1>
            <div>
                <Input.Search className='w-64' placeholder="Search websites" onSearch={(value) => setWebsiteSearch(value)} loading={isLoading} />

            </div>
        </header>
        <main className='h-[calc(100vh-12rem)] overflow-y-auto'>


            <Table<WebsiteType>
                rowKey="id"
                columns={columns}
                dataSource={websites || []}
                loading={isLoading}
                pagination={false}
                locale={{ emptyText: 'No websites found.' }}
            />
        </main>
        <footer className="mt-4 justify-center flex">
            <Pagination showSizeChanger defaultCurrent={WebsitePage} total={websitesTotal || 0} onShowSizeChange={(current, pageSize) => {
                setWebsiteLimit(pageSize);
            }} onChange={(current) => setWebsitePage(current)} />
        </footer>
    </div>;
}
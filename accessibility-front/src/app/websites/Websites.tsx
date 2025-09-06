"use client"
import PageError from '@/components/PageError';
import { User } from '@/lib/types/user';
import { Website as WebsiteType } from '@/lib/types/website';
import { useWebsites } from '@/providers/Websites';
import { Input, Pagination, Table } from 'antd';
import { Content } from "antd/es/layout/layout";
import { formatDate } from 'date-fns';
import CreateWebsite from './modals/createWebsite';
type Props = {
    user: User | null;
}

const columns = [
    {
        title: 'URL',
        dataIndex: 'url',
        key: 'url',
        render: (text: string, record: WebsiteType) => (
            <a href={`/websites/${record.id}`}>{text}</a>
        ),
    },
    {
        title: 'Last Scanned',
        dataIndex: 'last_scanned',
        key: 'last_scanned',
        render: (date: string) => {
            if (!date) return 'Never';
            return formatDate(new Date(date), 'MMMM dd, yyyy');
        },
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
        sorter: (a: WebsiteType, b: WebsiteType) =>
            a.report_counts.violations.total - b.report_counts.violations.total,
    },
    {
        title: 'Active',
        dataIndex: 'active',
        key: 'active',
        render: (active: boolean) => (active ? 'Yes' : 'No'),
    },
];  


function Websites({ user }: Props) {
    const {
        websites,
        websitesTotal,
        setWebsitePage,
        setWebsiteLimit,
        WebsitePage,
        isLoading,
        setWebsiteSearch,
    } = useWebsites();

    return (
        <Content className="">
            <header className="mb-4 flex w-full justify-between">
                <h1 className="text-2xl font-bold">Websites</h1>

                <div className="flex items-center gap-2">
                    <CreateWebsite user={user} />
                    <Input.Search
                        className="w-64"
                        placeholder="Search websites"
                        onSearch={(value) => setWebsiteSearch(value)}
                        loading={isLoading}
                    />
                </div>
            </header>
            <Content className="h-[calc(100vh-12rem)] overflow-y-auto">
                <Table<WebsiteType>
                    rowKey="id"
                    columns={columns}
                    dataSource={websites || []}
                    loading={isLoading}
                    pagination={false}
                    locale={{
                        emptyText: (
                            <PageError
                                status={'info'}
                                title="No Websites Found"
                                subTitle="It seems we couldn't find any websites."
                            />
                        ),
                    }}
                />
            </Content>
            <footer className="mt-4 flex justify-center">
                <Pagination
                    showSizeChanger
                    defaultCurrent={WebsitePage}
                    total={websitesTotal || 0}
                    onShowSizeChange={(current, pageSize) => {
                        setWebsiteLimit(pageSize);
                    }}
                    onChange={(current) => setWebsitePage(current)}
                />
            </footer>
        </Content>
    );
}

export default Websites
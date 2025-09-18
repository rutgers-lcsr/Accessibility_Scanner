'use client';
import PageError from '@/components/PageError';
import { User } from '@/lib/types/user';
import { Website as WebsiteType } from '@/lib/types/website';
import { useWebsites } from '@/providers/Websites';
import { Flex, Input, Pagination, Table } from 'antd';
import { Content } from 'antd/es/layout/layout';
import { formatDate } from 'date-fns';
import CreateWebsite from './modals/createWebsite';
type Props = {
    user: User | null;
};

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
        <Content className="p-6">
            <header className="mb-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                <h1 className="text-3xl font-bold text-gray-800">Websites</h1>
                <div className="flex items-center gap-3">
                    <CreateWebsite user={user} />
                    <Input.Search
                        className="w-72"
                        placeholder="Search websites"
                        onSearch={(value) => setWebsiteSearch(value)}
                        loading={isLoading}
                        allowClear
                        size="large"
                    />
                </div>
            </header>
            <Content>
                <Table<WebsiteType>
                    rowKey="id"
                    columns={columns}
                    dataSource={websites || []}
                    loading={isLoading}
                    pagination={false}
                    bordered
                    size="middle"
                    className="bg-white rounded-lg"
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
                <Flex style={{ padding: '16px 0' }} justify="center">
                    <Pagination
                        showSizeChanger
                        defaultCurrent={WebsitePage}
                        total={websitesTotal || 0}
                        onShowSizeChange={(current, pageSize) => {
                            setWebsiteLimit(pageSize);
                        }}
                        onChange={(current) => setWebsitePage(current)}
                    />
                </Flex>
            </Content>
        </Content>
    );
}

export default Websites;

'use client';
import PageError from '@/components/PageError';
import PageHeading from '@/components/PageHeading';
import { PageSize, pageSizeOptions } from '@/lib/browser';
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
        WebsiteLimit,
        setWebsiteLimit,
        WebsitePage,
        isLoading,
        setWebsiteSearch,
    } = useWebsites();

    return (
        <>
            <PageHeading title="Websites" />
            <Content className="p-6">
                <Flex
                    className="mb-4"
                    justify="end"
                    align="flex-end"
                    gap="small"
                    style={{ minWidth: '300px', marginBottom: '16px' }}
                >
                    <Flex gap="middle" align="center">
                        <CreateWebsite user={user} />
                        <Input.Search
                            className="w-72"
                            placeholder="Search websites"
                            onSearch={(value) => setWebsiteSearch(value)}
                            loading={isLoading}
                            allowClear
                            size="large"
                            aria-label="Search websites"
                        />
                    </Flex>
                </Flex>

                <div className="bg-white p-4 rounded-lg shadow">
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
                                setWebsiteLimit(pageSize as PageSize);
                            }}
                            pageSize={WebsiteLimit}
                            pageSizeOptions={pageSizeOptions}
                            onChange={(current) => setWebsitePage(current)}
                        />
                    </Flex>
                </div>
            </Content>
        </>
    );
}

export default Websites;

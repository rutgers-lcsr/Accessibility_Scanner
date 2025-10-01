'use client';
import PageError from '@/components/PageError';
import PageHeading from '@/components/PageHeading';
import { PageSize, pageSizeOptions } from '@/lib/browser';
import { User } from '@/lib/types/user';
import { Website as WebsiteType } from '@/lib/types/website';
import { useWebsites } from '@/providers/Websites';
import {
    Button,
    Flex,
    Input,
    Pagination,
    Select,
    Table,
    TableColumnType,
    Tag,
    Tooltip,
} from 'antd';
import { Content } from 'antd/es/layout/layout';
import { formatDate } from 'date-fns';
import CreateWebsite from './modals/createWebsite';
type Props = {
    user: User | null;
};

function Websites({ user }: Props) {
    const {
        websites,
        websitesTotal,
        setWebsitePage,
        WebsiteLimit,
        setWebsiteLimit,
        setWebsiteCategories,
        setWebsiteOrderBy,
        categories,
        WebsitePage,
        isLoading,
        setWebsiteSearch,
        exportCSV,
    } = useWebsites();

    const columns: TableColumnType<WebsiteType>[] = [
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
        },
        {
            title: 'Active',
            dataIndex: 'active',
            key: 'active',
            render: (active: boolean) => (active ? 'Yes' : 'No'),
        },
        {
            title: 'Categories',
            dataIndex: 'categories',
            key: 'categories',
            render: (categories: string[]) => (
                <span>
                    {categories.map((category) => (
                        <Tag key={category}>{category}</Tag>
                    ))}
                </span>
            ),
        },
    ];

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
                        <Select
                            className="w-96"
                            placeholder="Filter by category"
                            onChange={(value) => setWebsiteCategories(value)}
                            allowClear
                            mode="multiple"
                        >
                            {categories?.map((category) => (
                                <Select.Option key={category} value={category}>
                                    {category}
                                </Select.Option>
                            ))}
                        </Select>
                        <Tooltip title="Sort By">
                            <Select
                                className="w-96"
                                placeholder="Order by"
                                onChange={(value) => {
                                    if (
                                        value === 'url' ||
                                        value === 'violations' ||
                                        value === 'last_scanned'
                                    ) {
                                        setWebsiteOrderBy(value);
                                    }
                                }}
                                defaultValue="url"
                                size="middle"
                            >
                                <Select.Option value="url">URL</Select.Option>
                                <Select.Option value="violations">Violations</Select.Option>
                                <Select.Option value="last_scanned">Last Scanned</Select.Option>
                            </Select>
                        </Tooltip>

                        <Input.Search
                            className="w-96"
                            placeholder="Search websites"
                            onSearch={(value) => setWebsiteSearch(value)}
                            loading={isLoading}
                            allowClear
                            size="large"
                            aria-label="Search websites"
                        />
                        {user?.is_admin && (
                            <Tooltip title="Export Current Page as CSV">
                                <Button
                                    onClick={(e) => {
                                        e.preventDefault();
                                        exportCSV();
                                    }}
                                    size="middle"
                                    aria-label="Export websites as CSV"
                                    disabled={isLoading || (websites?.length || 0) === 0}
                                    type="primary"
                                >
                                    Export CSV
                                </Button>
                            </Tooltip>
                        )}
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

'use client';
import PageError from '@/components/PageError';
import { PageSize, pageSizeOptions } from '@/lib/browser';
import { Domain } from '@/lib/types/domain';
import { useDomains } from '@/providers/Domain';
import { Button, Flex, Input, Pagination, Table, TableColumnsType } from 'antd';
import { Content } from 'antd/es/layout/layout';
import AddDomain from './modals/addDomain';
import DeleteDomain from './modals/deleteDomain';

export default function Domains() {
    const {
        domains,
        loadingDomain,
        domainPage,
        domainCount,
        setDomainPage,
        domainLimit,
        setDomainLimit,
        setDomainFilters,
        patchDomain,
    } = useDomains();

    // Table columns
    const columns: TableColumnsType<Domain> = [
        {
            title: 'Domain',
            dataIndex: 'domain',
            key: 'domain',
            width: '40%',
        },
        {
            title: 'Parent',
            dataIndex: 'parent',
            key: 'parent',
            width: '10%',
            render: (parent: Domain) => {
                return <span>{parent?.domain || 'Is Parent'}</span>;
            },
        },
        {
            title: 'Actions',
            key: 'actions',
            width: '15%',
            render: (_, record) => {
                return (
                    <div className="flex justify-center gap-4">
                        <Button
                            onClick={() => patchDomain(record.id, { active: !record.active })}
                            type={record.active ? 'primary' : 'default'}
                        >
                            {record.active ? 'Deactivate' : 'Activate'}
                        </Button>
                        <DeleteDomain domainId={record.id} />
                    </div>
                );
            },
        },
    ];

    return (
        <Content className="p-6">
            <header className="mb-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                <h1 className="text-3xl font-bold text-gray-800">Domains</h1>
                <div></div>
                <div className="flex items-center gap-3">
                    <AddDomain />
                    <Input.Search
                        className="w-72"
                        placeholder="Search domains"
                        onSearch={(value) => {
                            // console.log(value);
                            setDomainFilters({ search: value });
                        }}
                        loading={loadingDomain}
                        allowClear
                        size="large"
                    />
                </div>
            </header>
            <Content>
                <Table<Domain>
                    rowKey="id"
                    columns={columns}
                    dataSource={domains || []}
                    bordered
                    size="middle"
                    loading={loadingDomain}
                    pagination={false}
                    locale={{ emptyText: <PageError status={'info'} title="No Domains found." /> }}
                />
                <Flex style={{ padding: '16px 0' }} justify="center">
                    <Pagination
                        showSizeChanger
                        defaultCurrent={domainPage}
                        total={domainCount}
                        pageSize={domainLimit}
                        pageSizeOptions={pageSizeOptions}
                        onShowSizeChange={(current, pageSize) => {
                            setDomainLimit(pageSize as PageSize);
                        }}
                        onChange={(current) => setDomainPage(current)}
                    />
                </Flex>
            </Content>
        </Content>
    );
}

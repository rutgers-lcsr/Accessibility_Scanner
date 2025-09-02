import PageError from "@/components/PageError";
import { Domain } from "@/lib/types/domain";
import { useDomains } from "@/providers/Domain";
import { Button, Input, Pagination, Table, TableColumnsType } from "antd";
import AddDomain from "./modals/addDomain";
import DeleteDomain from "./modals/deleteDomain";


export default function Domains() {
const {
        domains,
        loadingDomain,
        domainPage,
        domainCount,
        setDomainPage,
        setDomainLimit,
        setDomainFilters,
        patchDomain,
        deleteDomain,
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
                        <Button type={record.active ? 'primary' : 'default'}>
                            {record.active ? 'Deactivate' : 'Activate'}
                        </Button>
                        <DeleteDomain domainId={record.id} />
                    </div>
                );
            },
        },
    ];

    return (
        <div className="">
            <header className="mb-4 flex w-full justify-between">
                <h1 className="text-2xl font-bold">Domains</h1>
                <div></div>
                <div className="flex items-center gap-2">
                    <AddDomain />

                    <Input.Search
                        className="w-64"
                        placeholder="Search domains"
                        onSearch={(value) => {
                            // console.log(value);
                            setDomainFilters({ search: value });
                        }}
                        loading={loadingDomain}
                    />
                </div>
            </header>
            <main className="h-[calc(100vh-12rem)] overflow-y-auto">
                <Table<Domain>
                    rowKey="id"
                    columns={columns}
                    dataSource={domains || []}
                    loading={loadingDomain}
                    pagination={false}
                    locale={{ emptyText: <PageError status={'info'} title="No Domains found." /> }}
                />
            </main>
            <footer className="mt-4 flex justify-center">
                <Pagination
                    showSizeChanger
                    defaultCurrent={domainPage}
                    total={domainCount}
                    onShowSizeChange={(current, pageSize) => {
                        setDomainLimit(pageSize);
                    }}
                    onChange={(current) => setDomainPage(current)}
                />
            </footer>
        </div>
    );
}
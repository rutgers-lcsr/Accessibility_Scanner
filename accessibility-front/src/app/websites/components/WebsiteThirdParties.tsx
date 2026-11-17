'use client';
import PageError from '@/components/PageError';
import PageLoading from '@/components/PageLoading';
import { fetcherApi } from '@/lib/api';
import { ThirdPartyHost, VENDOR_STATUS_LABELS } from '@/lib/types/inventory';
import { PublicUser } from '@/lib/types/user';
import { useUser } from '@/providers/User';
import { Alert, Table, Tag } from 'antd';
import useSWR from 'swr';

type Props = {
    websiteId: number;
    user: PublicUser | null;
};

// Other hosts the website's pages load code, frames or styles from or send forms to,
// each with the vendor it belongs to and that vendor's accessibility report status.
function WebsiteThirdParties({ websiteId, user }: Props) {
    const { handlerUserApiRequest } = useUser();
    const { data, error } = useSWR(
        `/api/websites/${websiteId}/third-parties/`,
        user ? handlerUserApiRequest<ThirdPartyHost[]> : fetcherApi<ThirdPartyHost[]>
    );
    if (error) return <PageError status={500} title="Error loading third parties" />;
    if (!data) return <PageLoading minimal />;
    const unassigned = data.filter((row) => !row.vendor).length;

    return (
        <>
            {unassigned > 0 && (
                <Alert
                    style={{ marginTop: 8, marginBottom: 16 }}
                    type="info"
                    showIcon
                    title={`${unassigned} host${unassigned === 1 ? ' is' : 's are'} not in the vendor register`}
                    description="Third-party widgets are part of the website for accessibility purposes. Site admins can add these hosts under Settings, Vendors, with the vendor's accessibility conformance report (VPAT/ACR)."
                />
            )}
            <Table<ThirdPartyHost>
                rowKey="id"
                pagination={{ pageSize: 20, hideOnSinglePage: true }}
                dataSource={data}
                locale={{ emptyText: 'This website loads nothing from other hosts.' }}
                columns={[
                    {
                        title: 'Host',
                        dataIndex: 'host',
                        key: 'host',
                        render: (host: string, row) => (
                            <>
                                <div className="font-medium break-all">{host}</div>
                                {row.example_url && (
                                    <div className="text-xs break-all text-gray-600">
                                        {row.example_url}
                                    </div>
                                )}
                            </>
                        ),
                    },
                    {
                        title: 'Used for',
                        dataIndex: 'kinds',
                        key: 'kinds',
                        render: (kinds: string[]) =>
                            kinds.map((kind) => <Tag key={kind}>{kind}</Tag>),
                    },
                    {
                        title: 'Pages',
                        dataIndex: 'page_count',
                        key: 'pages',
                    },
                    {
                        title: 'Vendor',
                        dataIndex: 'vendor',
                        key: 'vendor',
                        render: (vendor: ThirdPartyHost['vendor']) =>
                            vendor ? (
                                <>
                                    <div>{vendor.name}</div>
                                    <div className="mt-1 flex flex-wrap gap-1">
                                        <Tag
                                            color={
                                                vendor.status === 'approved'
                                                    ? 'green'
                                                    : vendor.status === 'not_approved'
                                                      ? 'red'
                                                      : 'orange'
                                            }
                                        >
                                            {VENDOR_STATUS_LABELS[vendor.status]}
                                        </Tag>
                                        {!vendor.has_vpat && <Tag color="orange">No VPAT/ACR</Tag>}
                                        {vendor.review_overdue && (
                                            <Tag color="red">Review overdue</Tag>
                                        )}
                                    </div>
                                </>
                            ) : (
                                <span className="text-gray-600">Not registered</span>
                            ),
                    },
                ]}
            />
        </>
    );
}

export default WebsiteThirdParties;

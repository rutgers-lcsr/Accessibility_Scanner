'use client';
import { LinkCell } from '@/components/LinkCell';
import { LinkStatusTag } from '@/components/LinkStatusTag';
import { LinkStatus, PageLink } from '@/lib/types/link';
import { Alert, Table, TableColumnType } from 'antd';

type Props = {
    links: PageLink[];
};

// The links one page carries, broken first, for the page report.
export default function PageLinks({ links }: Props) {
    const broken = links.filter((link) => link.status === 'broken').length;
    const columns: TableColumnType<PageLink>[] = [
        {
            title: 'Link',
            dataIndex: 'url',
            key: 'url',
            width: 480,
            render: (url: string, record: { external: boolean; final_url: string | null }) => (
                <LinkCell url={url} external={record.external} final_url={record.final_url} />
            ),
        },
        {
            title: 'Link text',
            dataIndex: 'text',
            key: 'text',
            render: (text: string | null) => text ?? <span className="text-gray-400">(no text)</span>,
        },
        {
            title: 'Status',
            dataIndex: 'status',
            key: 'status',
            render: (status: LinkStatus, record: PageLink) => (
                <LinkStatusTag status={status} code={record.status_code} error={record.error} />
            ),
        },
    ];

    return (
        <>
            {broken > 0 && (
                <Alert
                    style={{ marginBottom: 16 }}
                    type="warning"
                    showIcon
                    message={`${broken} broken link${broken === 1 ? '' : 's'} on this page`}
                    description="These lead to a page that no longer exists. Fix or remove them."
                />
            )}
            <Table<PageLink>
                style={{ width: '100%' }}
                size="small"
                columns={columns}
                dataSource={links}
                rowKey="id"
                pagination={links.length > 20 ? { pageSize: 20 } : false}
                locale={{ emptyText: 'No links were recorded for this page.' }}
            />
        </>
    );
}

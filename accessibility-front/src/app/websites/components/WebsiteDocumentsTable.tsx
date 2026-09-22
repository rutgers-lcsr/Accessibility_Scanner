'use client';
import PageError from '@/components/PageError';
import PageLoading from '@/components/PageLoading';
import { fetcherApi } from '@/lib/api';
import { Paged } from '@/lib/types/Paged';
import { DocumentStatus, WebsiteDocument } from '@/lib/types/document';
import { PublicUser } from '@/lib/types/user';
import { useUser } from '@/providers/User';
import {
    CheckCircleOutlined,
    CloseCircleOutlined,
    MinusCircleOutlined,
    QuestionCircleOutlined,
    StopOutlined,
    SyncOutlined,
    WarningOutlined,
} from '@ant-design/icons';
import { Pagination, Table, TableColumnType, Tag, Tooltip } from 'antd';
import React from 'react';
import useSWR from 'swr';

type Props = {
    websiteId: number;
    user: PublicUser | null;
};

// Status as icon + label, never colour alone.
function DocumentStatusTag({ status, error }: { status: DocumentStatus; error: string | null }) {
    const meta: Record<DocumentStatus, { label: string; color?: string; icon: React.ReactNode }> = {
        tagged: { label: 'Tagged', color: 'green', icon: <CheckCircleOutlined /> },
        untagged: { label: 'Untagged', color: 'red', icon: <CloseCircleOutlined /> },
        pending: { label: 'Not checked yet', icon: <SyncOutlined /> },
        unreachable: { label: 'Unreachable', color: 'orange', icon: <WarningOutlined /> },
        too_large: { label: 'Too large to check', color: 'orange', icon: <StopOutlined /> },
        unreadable: { label: 'Unreadable', color: 'orange', icon: <QuestionCircleOutlined /> },
        skipped: { label: 'Skipped (robots.txt)', icon: <MinusCircleOutlined /> },
        not_checked: { label: 'Not checked', icon: <MinusCircleOutlined /> },
    };
    const m = meta[status] ?? { label: status, icon: <MinusCircleOutlined /> };
    const tag = (
        <Tag color={m.color} icon={m.icon}>
            {m.label}
        </Tag>
    );
    return error ? <Tooltip title={error}>{tag}</Tooltip> : tag;
}

function size(bytes: number | null): string {
    if (bytes === null) return '';
    if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    return `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

// The documents a website's pages link to, with the PDF checks.
function WebsiteDocumentsTable({ websiteId, user }: Props) {
    const { handlerUserApiRequest } = useUser();
    const [currentPage, setCurrentPage] = React.useState(1);
    const [pageSize, setPageSize] = React.useState(10);

    const { data, error, isLoading } = useSWR(
        `/api/websites/${websiteId}/documents?page=${currentPage}&limit=${pageSize}`,
        user ? handlerUserApiRequest<Paged<WebsiteDocument>> : fetcherApi<Paged<WebsiteDocument>>
    );

    const columns: TableColumnType<WebsiteDocument>[] = [
        {
            title: 'Document',
            dataIndex: 'url',
            key: 'url',
            width: 360,
            render: (url: string, record: WebsiteDocument) => (
                <>
                    <a href={url} target="_blank" rel="noopener noreferrer" className="break-all">
                        {url}
                    </a>
                    {record.title && <div className="text-xs text-gray-500">{record.title}</div>}
                </>
            ),
        },
        {
            title: 'Type',
            dataIndex: 'type',
            key: 'type',
            render: (type: string) => <Tag>{type.toUpperCase()}</Tag>,
        },
        {
            title: 'Status',
            dataIndex: 'status',
            key: 'status',
            render: (status: DocumentStatus, record: WebsiteDocument) => (
                <DocumentStatusTag status={status} error={record.error} />
            ),
        },
        {
            title: 'Title',
            dataIndex: 'has_title',
            key: 'has_title',
            render: (has: boolean | null) => (has === null ? '' : has ? 'Yes' : 'No'),
        },
        {
            title: 'Language',
            dataIndex: 'language',
            key: 'language',
            render: (v: string | null) => v ?? '',
        },
        {
            title: 'Pages',
            dataIndex: 'page_count',
            key: 'page_count',
            align: 'right',
            render: (v: number | null) => v ?? '',
        },
        { title: 'Size', dataIndex: 'size_bytes', key: 'size_bytes', align: 'right', render: size },
        {
            title: 'Linked from',
            dataIndex: 'found_on',
            key: 'found_on',
            render: (found: string[]) => (
                <Tooltip title={found.join('\n')}>
                    <span>
                        {found.length} {found.length === 1 ? 'page' : 'pages'}
                    </span>
                </Tooltip>
            ),
        },
        {
            title: 'Last checked',
            dataIndex: 'checked_at',
            key: 'checked_at',
            render: (v: string | null) => (v ? new Date(v).toLocaleDateString() : ''),
        },
    ];

    if (error) return <PageError status={500} title="Error loading documents" />;
    if (!data) return <PageLoading minimal />;

    return (
        <>
            <Table<WebsiteDocument>
                style={{ width: '100%' }}
                pagination={false}
                columns={columns}
                dataSource={data.items}
                loading={isLoading}
                rowKey="id"
                locale={{ emptyText: 'No documents are linked from this website.' }}
            />
            <div className="flex justify-center pt-4 pb-4">
                <Pagination
                    showSizeChanger
                    current={currentPage}
                    pageSize={pageSize}
                    total={data.count || 0}
                    onShowSizeChange={(current, newPageSize) => setPageSize(newPageSize)}
                    onChange={(page) => setCurrentPage(page)}
                />
            </div>
        </>
    );
}

export default WebsiteDocumentsTable;

'use client';
import { ApiKey, CreatedApiKey } from '@/lib/types/user';
import { useUser } from '@/providers/User';
import { ApiOutlined, CopyOutlined, KeyOutlined, PlusOutlined } from '@ant-design/icons';
import {
    Alert,
    Button,
    Card,
    Input,
    Modal,
    Popconfirm,
    Table,
    Tag,
    Typography,
    message,
} from 'antd';
import { useState } from 'react';
import useSWR from 'swr';

const KEYS_URL = '/api/users/me/api-keys/';
// Swagger UI is served by the backend under /api/ so the Next proxy forwards it.
const DOCS_URL = '/api/docs/';

function formatDate(value: string | null) {
    if (!value) return 'Never';
    return new Date(value).toLocaleString();
}

function ApiKeys() {
    const { handlerUserApiRequest } = useUser();
    const { data, isLoading, mutate } = useSWR<ApiKey[]>(KEYS_URL, (url: string) =>
        handlerUserApiRequest<ApiKey[]>(url)
    );

    const [createOpen, setCreateOpen] = useState(false);
    const [name, setName] = useState('');
    const [creating, setCreating] = useState(false);
    const [newKey, setNewKey] = useState<CreatedApiKey | null>(null);

    const handleCreate = async () => {
        if (!name.trim()) {
            message.error('Please enter a name');
            return;
        }
        setCreating(true);
        try {
            const created = await handlerUserApiRequest<CreatedApiKey>(KEYS_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: name.trim() }),
            });
            setCreateOpen(false);
            setName('');
            setNewKey(created);
            mutate();
        } catch {
            message.error('Failed to create API key');
        } finally {
            setCreating(false);
        }
    };

    const handleRevoke = async (id: number) => {
        try {
            await handlerUserApiRequest(`${KEYS_URL}${id}/`, { method: 'DELETE' });
            message.success('API key revoked');
            mutate();
        } catch {
            message.error('Failed to revoke API key');
        }
    };

    const handleCopy = async (text: string) => {
        try {
            await navigator.clipboard.writeText(text);
            message.success('Copied to clipboard');
        } catch {
            message.error('Failed to copy to clipboard');
        }
    };

    const columns = [
        { title: 'Name', dataIndex: 'name', key: 'name' },
        {
            title: 'Key',
            dataIndex: 'prefix',
            key: 'prefix',
            render: (prefix: string) => <Tag>{prefix}…</Tag>,
        },
        {
            title: 'Last used',
            dataIndex: 'last_used_at',
            key: 'last_used_at',
            render: formatDate,
        },
        {
            title: 'Created',
            dataIndex: 'created_at',
            key: 'created_at',
            render: formatDate,
        },
        {
            title: 'Actions',
            key: 'actions',
            render: (_: unknown, record: ApiKey) => (
                <Popconfirm
                    title="Revoke this API key?"
                    description="Any application using it will stop working."
                    okText="Revoke"
                    okButtonProps={{ danger: true }}
                    onConfirm={() => handleRevoke(record.id)}
                >
                    <Button danger size="small">
                        Revoke
                    </Button>
                </Popconfirm>
            ),
        },
    ];

    const origin = typeof window !== 'undefined' ? window.location.origin : 'https://<host>';

    return (
        <div className="w-full">
            <Card
                title={
                    <span>
                        <KeyOutlined /> Your API Keys
                    </span>
                }
                extra={
                    <Button
                        type="primary"
                        icon={<PlusOutlined />}
                        onClick={() => setCreateOpen(true)}
                    >
                        Create API Key
                    </Button>
                }
            >
                <Table
                    rowKey="id"
                    loading={isLoading}
                    dataSource={data || []}
                    columns={columns}
                    pagination={false}
                />
            </Card>

            <Card
                title="Using your API key"
                className="mt-6"
                extra={
                    <Button
                        type="primary"
                        icon={<ApiOutlined />}
                        href={DOCS_URL}
                        target="_blank"
                    >
                        Full API reference
                    </Button>
                }
            >
                <Typography.Paragraph type="secondary">
                    Send your key in the <code>X-API-Key</code> request header (or as{' '}
                    <code>Authorization: Bearer &lt;key&gt;</code>). A key acts as you — it can read
                    any report your account has access to, and nothing more. Treat it like a
                    password; revoke it here at any time to disable it immediately.
                </Typography.Paragraph>
                <Typography.Paragraph type="secondary">
                    Add <code>?format=</code> to any endpoint: <code>json</code> (default),{' '}
                    <code>markdown</code>, <code>agent</code> (AI fix prompt), or <code>pdf</code>{' '}
                    (the website aggregate does not support pdf). The{' '}
                    <Typography.Link href={DOCS_URL} target="_blank">
                        interactive API reference
                    </Typography.Link>{' '}
                    lists every endpoint and lets you try requests in the browser.
                </Typography.Paragraph>
                <Typography.Paragraph type="secondary">
                    Use a <strong>website</strong> ID (shown in the app) with the{' '}
                    <code>/websites/…</code> endpoints for a whole-site report; the{' '}
                    <code>/sites/…</code> endpoints take an individual <strong>page</strong> (site)
                    ID.
                </Typography.Paragraph>
                <pre className="overflow-auto rounded bg-gray-100 p-4 text-xs whitespace-pre-wrap">
                    {`# Report by ID (JSON)
curl -H "X-API-Key: <YOUR_KEY>" \\
  ${origin}/api/v1/reports/123

# Same report as an AI fix prompt
curl -H "X-API-Key: <YOUR_KEY>" \\
  "${origin}/api/v1/reports/123?format=agent"

# Download the PDF
curl -H "X-API-Key: <YOUR_KEY>" \\
  "${origin}/api/v1/reports/123?format=pdf" -o report.pdf

# Whole-website report (all pages combined)
curl -H "X-API-Key: <YOUR_KEY>" \\
  "${origin}/api/v1/websites/7/report?format=agent"

# Latest report for each page of a website
curl -H "X-API-Key: <YOUR_KEY>" \\
  ${origin}/api/v1/websites/7/reports/latest

# Latest report for a single page, by site ID or URL
curl -H "X-API-Key: <YOUR_KEY>" \\
  ${origin}/api/v1/sites/45/reports/latest
curl -H "X-API-Key: <YOUR_KEY>" \\
  "${origin}/api/v1/reports/latest?url=https://example.com/page"

# Trigger a scan, then poll status, then fetch the report
curl -X POST -H "X-API-Key: <YOUR_KEY>" \\
  ${origin}/api/v1/websites/7/scan
curl -H "X-API-Key: <YOUR_KEY>" \\
  ${origin}/api/v1/scans/<TASK_ID>   # state: SUCCESS when done
curl -H "X-API-Key: <YOUR_KEY>" \\
  "${origin}/api/v1/websites/7/reports/latest?format=agent"`}
                </pre>
            </Card>

            <Modal
                title="Create API Key"
                open={createOpen}
                onCancel={() => setCreateOpen(false)}
                onOk={handleCreate}
                confirmLoading={creating}
                okText="Create"
            >
                <p className="mb-2 text-sm text-gray-500">
                    Give your key a name so you can recognize it later.
                </p>
                <Input
                    placeholder="e.g. CI pipeline"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    onPressEnter={handleCreate}
                />
            </Modal>

            <Modal
                title="API Key Created"
                open={!!newKey}
                onCancel={() => setNewKey(null)}
                footer={[
                    <Button key="close" onClick={() => setNewKey(null)}>
                        Close
                    </Button>,
                    <Button
                        key="copy"
                        type="primary"
                        icon={<CopyOutlined />}
                        onClick={() => newKey && handleCopy(newKey.key)}
                    >
                        Copy
                    </Button>,
                ]}
            >
                <Alert
                    type="warning"
                    showIcon
                    className="mb-4"
                    message="Copy your key now"
                    description="This is the only time the full key will be shown. Store it somewhere safe."
                />
                <pre className="overflow-auto rounded bg-gray-100 p-4 text-xs break-all whitespace-pre-wrap">
                    {newKey?.key}
                </pre>
            </Modal>
        </div>
    );
}

export default ApiKeys;

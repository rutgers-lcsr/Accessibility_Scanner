'use client';
import PageLoading from '@/components/PageLoading';
import { namedExpandIcon } from '@/components/namedExpandIcon';
import { Field } from '@/app/websites/components/PanelFields';
import { UnassignedHost, Vendor, VENDOR_STATUS_LABELS, VendorStatus } from '@/lib/types/inventory';
import { useAlerts } from '@/providers/Alerts';
import { useUser } from '@/providers/User';
import { Button, Input, Modal, Popconfirm, Select, Table, Tag } from 'antd';
import { useState } from 'react';
import useSWR from 'swr';

// Which websites use the host, before deciding whether it is a vendor.
const VendorExpandIcon = namedExpandIcon<Vendor>((vendor) => `Websites using ${vendor.name}`);

type UsageSite = {
    website_id: number;
    url: string;
    pages: number;
    kinds: string[];
    hosts?: string[];
    example_pages?: string[];
};

// The websites using a vendor or a host: each links to its third-party list, with how many
// pages use it, for what, and (for a vendor) through which of its hosts.
function SiteUsage({ sites, hidden = 0 }: { sites: UsageSite[]; hidden?: number }) {
    return (
        <>
            <ul className="m-0 list-none space-y-2 p-0">
                {sites.map((site) => (
                    <li key={site.website_id}>
                        <a
                            className="underline"
                            href={`/websites/${site.website_id}?tab=third-parties`}
                        >
                            {site.url}
                        </a>
                        <span className="ml-2 text-sm text-gray-700">
                            {site.pages} page{site.pages === 1 ? '' : 's'}
                            {site.hosts?.length ? ` · via ${site.hosts.join(', ')}` : ''}
                        </span>
                        {site.kinds.map((kind) => (
                            <Tag key={kind} style={{ marginLeft: 8 }}>
                                {kind}
                            </Tag>
                        ))}
                        {!!site.example_pages?.length && (
                            <details className="mt-1 text-sm">
                                <summary className="cursor-pointer text-gray-700">
                                    Example pages
                                </summary>
                                <ul className="mt-1 mb-0 pl-5">
                                    {site.example_pages.map((page) => (
                                        <li key={page} className="break-all">
                                            {page}
                                        </li>
                                    ))}
                                </ul>
                            </details>
                        )}
                    </li>
                ))}
            </ul>
            {hidden > 0 && (
                <p className="mt-2 mb-0 text-sm text-gray-700">
                    And {hidden} more website{hidden === 1 ? '' : 's'} you do not have access to.
                </p>
            )}
        </>
    );
}

const UnassignedHostExpandIcon = namedExpandIcon<UnassignedHost>(
    (host) => `Websites using ${host.host}`
);

type Draft = Omit<Vendor, 'id' | 'review_overdue' | 'websites' | 'hosts'> & {
    id?: number;
    hosts: string;
};

const EMPTY: Draft = {
    name: '',
    hosts: '',
    status: 'under_review',
    vpat_url: '',
    vpat_date: '',
    review_due: '',
    contact: '',
    notes: '',
};

const STATUS_COLOR: Record<VendorStatus, string> = {
    approved: 'green',
    under_review: 'orange',
    not_approved: 'red',
};

// The vendor register: third parties the websites load, with their accessibility
// conformance report (VPAT/ACR) and when it is next due for review. Hosts seen on the
// websites that match no vendor are listed below so they can be registered.
function Vendors() {
    const { handlerUserApiRequest } = useUser();
    const { addAlert } = useAlerts();
    const { data: vendors, mutate } = useSWR('/api/vendors/', handlerUserApiRequest<Vendor[]>);
    const { data: unassigned, mutate: mutateUnassigned } = useSWR(
        '/api/vendors/unassigned-hosts/',
        handlerUserApiRequest<UnassignedHost[]>
    );
    const [draft, setDraft] = useState<Draft | null>(null);
    const [saving, setSaving] = useState(false);

    const refresh = async () => {
        await Promise.all([mutate(), mutateUnassigned()]);
    };

    const save = async () => {
        if (!draft) return;
        setSaving(true);
        try {
            const { id, hosts, ...rest } = draft;
            await handlerUserApiRequest(id ? `/api/vendors/${id}/` : '/api/vendors/', {
                method: id ? 'PATCH' : 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ...rest, hosts: hosts.split(/\s+/).filter(Boolean) }),
            });
            await refresh();
            setDraft(null);
        } catch (e) {
            addAlert('Could not save: ' + (e as Error).message, 'error');
        }
        setSaving(false);
    };

    const remove = async (id: number) => {
        try {
            await handlerUserApiRequest(`/api/vendors/${id}/`, { method: 'DELETE' });
            await refresh();
        } catch (e) {
            addAlert('Could not delete: ' + (e as Error).message, 'error');
        }
    };

    if (!vendors) return <PageLoading minimal />;

    return (
        <div className="max-w-6xl space-y-8">
            <section aria-labelledby="vendor-register">
                <h2
                    id="vendor-register"
                    style={{ marginBottom: 8 }}
                    className="text-xl font-semibold"
                >
                    Vendor register
                </h2>
                <p style={{ marginBottom: 16 }} className="text-sm text-gray-600">
                    A host matches a vendor when it is one of the vendor&apos;s hosts or a subdomain
                    of one.
                </p>
                <Button type="primary" className="mb-4" onClick={() => setDraft({ ...EMPTY })}>
                    Add vendor
                </Button>
                <Table<Vendor>
                    rowKey="id"
                    dataSource={vendors}
                    pagination={false}
                    components={{ ExpandIcon: VendorExpandIcon }}
                    expandable={{
                        rowExpandable: (vendor) => (vendor.websites ?? 0) > 0,
                        expandedRowRender: (vendor) => (
                            <SiteUsage
                                sites={vendor.sites ?? []}
                                hidden={(vendor.websites ?? 0) - (vendor.sites?.length ?? 0)}
                            />
                        ),
                    }}
                    locale={{ emptyText: 'No vendors registered yet.' }}
                    columns={[
                        {
                            title: 'Vendor',
                            dataIndex: 'name',
                            key: 'name',
                            render: (name: string, row) => (
                                <>
                                    <div className="font-medium">{name}</div>
                                    <div className="text-xs text-gray-600">
                                        {row.hosts.join(', ')}
                                    </div>
                                </>
                            ),
                        },
                        {
                            title: 'Status',
                            dataIndex: 'status',
                            key: 'status',
                            render: (status: VendorStatus) => (
                                <Tag color={STATUS_COLOR[status]}>
                                    {VENDOR_STATUS_LABELS[status]}
                                </Tag>
                            ),
                        },
                        {
                            title: 'VPAT/ACR',
                            key: 'vpat',
                            render: (_, row) =>
                                row.vpat_url ? (
                                    <a href={row.vpat_url} target="_blank" rel="noreferrer">
                                        Report{row.vpat_date && ` (${row.vpat_date})`}
                                    </a>
                                ) : (
                                    <Tag color="orange">Missing</Tag>
                                ),
                        },
                        {
                            title: 'Review due',
                            dataIndex: 'review_due',
                            key: 'review_due',
                            render: (value: string | null, row) =>
                                value ? (
                                    <>
                                        {value}{' '}
                                        {row.review_overdue && <Tag color="red">Overdue</Tag>}
                                    </>
                                ) : (
                                    '—'
                                ),
                        },
                        { title: 'Websites', dataIndex: 'websites', key: 'websites' },
                        {
                            title: '',
                            key: 'actions',
                            render: (_, row) => (
                                <div className="flex gap-2">
                                    <Button
                                        size="small"
                                        onClick={() =>
                                            setDraft({
                                                ...row,
                                                hosts: row.hosts.join('\n'),
                                                vpat_url: row.vpat_url ?? '',
                                                vpat_date: row.vpat_date ?? '',
                                                review_due: row.review_due ?? '',
                                                contact: row.contact ?? '',
                                                notes: row.notes ?? '',
                                            })
                                        }
                                    >
                                        Edit
                                    </Button>
                                    <Popconfirm
                                        title="Delete this vendor?"
                                        onConfirm={() => remove(row.id)}
                                    >
                                        <Button size="small" danger>
                                            Delete
                                        </Button>
                                    </Popconfirm>
                                </div>
                            ),
                        },
                    ]}
                />
            </section>

            <section aria-labelledby="unassigned-hosts">
                <h2
                    id="unassigned-hosts"
                    style={{ marginBottom: 8 }}
                    className="text-xl font-semibold"
                >
                    Hosts not in the register
                </h2>
                <p style={{ marginBottom: 16 }} className="text-sm text-gray-600">
                    Hosts the websites load scripts, frames or styles from, or send forms to, that
                    match no vendor. Most used first.
                </p>
                <Table<UnassignedHost>
                    rowKey="host"
                    dataSource={unassigned ?? []}
                    loading={!unassigned}
                    pagination={{ pageSize: 20, hideOnSinglePage: true }}
                    locale={{ emptyText: 'Every host is matched to a vendor.' }}
                    components={{ ExpandIcon: UnassignedHostExpandIcon }}
                    expandable={{
                        expandedRowRender: (row) => <SiteUsage sites={row.sites} />,
                    }}
                    columns={[
                        { title: 'Host', dataIndex: 'host', key: 'host' },
                        {
                            title: 'Used for',
                            dataIndex: 'kinds',
                            key: 'kinds',
                            render: (kinds: string[]) =>
                                kinds.map((kind) => <Tag key={kind}>{kind}</Tag>),
                        },
                        { title: 'Websites', dataIndex: 'websites', key: 'websites' },
                        { title: 'Pages', dataIndex: 'pages', key: 'pages' },
                        {
                            title: '',
                            key: 'add',
                            render: (_, row) => (
                                <Button
                                    size="small"
                                    onClick={() => setDraft({ ...EMPTY, hosts: row.host })}
                                >
                                    Add as vendor
                                </Button>
                            ),
                        },
                    ]}
                />
            </section>

            <Modal
                open={draft !== null}
                title={draft?.id ? 'Edit vendor' : 'Add vendor'}
                okText="Save"
                confirmLoading={saving}
                onOk={save}
                onCancel={() => setDraft(null)}
                width={640}
            >
                {draft && (
                    <div className="space-y-4">
                        <Field id="vendor-name" label="Name">
                            <Input
                                id="vendor-name"
                                value={draft.name}
                                maxLength={200}
                                onChange={(e) => setDraft({ ...draft, name: e.target.value })}
                            />
                        </Field>
                        <Field
                            id="vendor-hosts"
                            label="Hosts"
                            help="One per line, e.g. kaltura.com. Subdomains match too."
                        >
                            <Input.TextArea
                                id="vendor-hosts"
                                rows={3}
                                value={draft.hosts}
                                onChange={(e) => setDraft({ ...draft, hosts: e.target.value })}
                            />
                        </Field>
                        <Field id="vendor-status" label="Status">
                            <Select<VendorStatus>
                                id="vendor-status"
                                style={{ width: '100%' }}
                                value={draft.status}
                                onChange={(status) => setDraft({ ...draft, status })}
                                options={(Object.keys(VENDOR_STATUS_LABELS) as VendorStatus[]).map(
                                    (value) => ({
                                        value,
                                        label: VENDOR_STATUS_LABELS[value],
                                    })
                                )}
                            />
                        </Field>
                        <Field id="vendor-vpat" label="VPAT/ACR link">
                            <Input
                                id="vendor-vpat"
                                value={draft.vpat_url ?? ''}
                                placeholder="https://"
                                onChange={(e) => setDraft({ ...draft, vpat_url: e.target.value })}
                            />
                        </Field>
                        <div className="grid grid-cols-2 gap-4">
                            <Field id="vendor-vpat-date" label="Report dated">
                                <Input
                                    id="vendor-vpat-date"
                                    type="date"
                                    value={draft.vpat_date ?? ''}
                                    onChange={(e) =>
                                        setDraft({ ...draft, vpat_date: e.target.value })
                                    }
                                />
                            </Field>
                            <Field id="vendor-review" label="Next review due">
                                <Input
                                    id="vendor-review"
                                    type="date"
                                    value={draft.review_due ?? ''}
                                    onChange={(e) =>
                                        setDraft({ ...draft, review_due: e.target.value })
                                    }
                                />
                            </Field>
                        </div>
                        <Field id="vendor-contact" label="Contact">
                            <Input
                                id="vendor-contact"
                                value={draft.contact ?? ''}
                                maxLength={300}
                                onChange={(e) => setDraft({ ...draft, contact: e.target.value })}
                            />
                        </Field>
                        <Field id="vendor-notes" label="Notes">
                            <Input.TextArea
                                id="vendor-notes"
                                rows={3}
                                value={draft.notes ?? ''}
                                onChange={(e) => setDraft({ ...draft, notes: e.target.value })}
                            />
                        </Field>
                    </div>
                )}
            </Modal>
        </div>
    );
}

export default Vendors;

'use client';
import PageLoading from '@/components/PageLoading';
import { Field } from '@/app/websites/components/PanelFields';
import { CHECK_TYPE_LABELS, ContentRequirement, RequirementCheckType } from '@/lib/types/health';
import { Paged } from '@/lib/types/Paged';
import { Website } from '@/lib/types/website';
import { useAlerts } from '@/providers/Alerts';
import { useUser } from '@/providers/User';
import { Button, Input, Modal, Popconfirm, Select, Switch, Table, Tag } from 'antd';
import { useState } from 'react';
import useSWR from 'swr';

type Draft = Omit<ContentRequirement, 'id'> & { id?: number };

const EMPTY: Draft = {
    name: '',
    description: '',
    check_type: 'link_text',
    pattern: '',
    enabled: true,
    website_ids: [],
};

const PATTERN_HELP: Record<RequirementCheckType, string> = {
    link_text: 'A regular expression, case-insensitive. Example: accessibility|report a barrier',
    link_href: 'A regular expression, case-insensitive. Example: rutgers\\.edu/accessibility',
    selector: 'A CSS selector. Example: footer a[href*="privacy"]',
    text: 'A regular expression, case-insensitive. Example: ©\\s*\\d{4}\\s*Rutgers',
};

// Site admins define what a website's home page must carry and pick the websites each
// requirement applies to; the health check reports the result on each website.
function Requirements() {
    const { handlerUserApiRequest } = useUser();
    const { addAlert } = useAlerts();
    const { data, mutate } = useSWR(
        '/api/requirements/',
        handlerUserApiRequest<ContentRequirement[]>
    );
    const { data: websites } = useSWR(
        '/api/websites/?limit=1000&orderBy=url',
        handlerUserApiRequest<Paged<Website>>
    );
    const [draft, setDraft] = useState<Draft | null>(null);
    const [saving, setSaving] = useState(false);

    const save = async () => {
        if (!draft) return;
        setSaving(true);
        try {
            const { id, ...body } = draft;
            await handlerUserApiRequest(id ? `/api/requirements/${id}/` : '/api/requirements/', {
                method: id ? 'PATCH' : 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });
            await mutate();
            setDraft(null);
            addAlert(
                'Requirement saved. Websites show the result after their next health check.',
                'success'
            );
        } catch (e) {
            addAlert('Could not save: ' + (e as Error).message, 'error');
        }
        setSaving(false);
    };

    const remove = async (id: number) => {
        try {
            await handlerUserApiRequest(`/api/requirements/${id}/`, { method: 'DELETE' });
            await mutate();
        } catch (e) {
            addAlert('Could not delete: ' + (e as Error).message, 'error');
        }
    };

    if (!data) return <PageLoading minimal />;

    return (
        <div className="max-w-5xl">
            <p className="mb-4 text-sm text-gray-600">
                What a website&apos;s home page must carry, such as a link to the accessibility
                statement or a privacy notice. A requirement applies only to the websites you pick
                for it.
            </p>
            <Button type="primary" className="mb-4" onClick={() => setDraft({ ...EMPTY })}>
                Add requirement
            </Button>
            <Table<ContentRequirement>
                rowKey="id"
                dataSource={data}
                pagination={false}
                locale={{ emptyText: 'No content requirements yet.' }}
                columns={[
                    {
                        title: 'Requirement',
                        dataIndex: 'name',
                        key: 'name',
                        render: (name: string, row) => (
                            <>
                                <div className="font-medium">
                                    {name} {!row.enabled && <Tag>Off</Tag>}
                                </div>
                                {row.description && (
                                    <div className="text-xs text-gray-500">{row.description}</div>
                                )}
                            </>
                        ),
                    },
                    {
                        title: 'Check',
                        key: 'check',
                        render: (_, row) => (
                            <>
                                <div className="text-sm">{CHECK_TYPE_LABELS[row.check_type]}</div>
                                <code className="text-xs break-all">{row.pattern}</code>
                            </>
                        ),
                    },
                    {
                        title: 'Websites',
                        dataIndex: 'website_ids',
                        key: 'websites',
                        render: (ids: number[]) => `${ids.length}`,
                    },
                    {
                        title: '',
                        key: 'actions',
                        render: (_, row) => (
                            <div className="flex gap-2">
                                <Button size="small" onClick={() => setDraft({ ...row })}>
                                    Edit
                                </Button>
                                <Popconfirm
                                    title="Delete this requirement?"
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
            <Modal
                open={draft !== null}
                title={draft?.id ? 'Edit requirement' : 'Add requirement'}
                okText="Save"
                confirmLoading={saving}
                onOk={save}
                onCancel={() => setDraft(null)}
                width={640}
            >
                {draft && (
                    <div className="space-y-4">
                        <Field id="req-name" label="Name">
                            <Input
                                id="req-name"
                                value={draft.name}
                                maxLength={200}
                                onChange={(e) => setDraft({ ...draft, name: e.target.value })}
                            />
                        </Field>
                        <Field id="req-description" label="Description">
                            <Input.TextArea
                                id="req-description"
                                rows={2}
                                value={draft.description ?? ''}
                                onChange={(e) =>
                                    setDraft({ ...draft, description: e.target.value })
                                }
                            />
                        </Field>
                        <Field id="req-type" label="The home page must have">
                            <Select<RequirementCheckType>
                                id="req-type"
                                style={{ width: '100%' }}
                                value={draft.check_type}
                                onChange={(value) => setDraft({ ...draft, check_type: value })}
                                options={(
                                    Object.keys(CHECK_TYPE_LABELS) as RequirementCheckType[]
                                ).map((value) => ({
                                    value,
                                    label: CHECK_TYPE_LABELS[value],
                                }))}
                            />
                        </Field>
                        <Field
                            id="req-pattern"
                            label="Pattern"
                            help={PATTERN_HELP[draft.check_type]}
                        >
                            <Input
                                id="req-pattern"
                                value={draft.pattern}
                                maxLength={500}
                                onChange={(e) => setDraft({ ...draft, pattern: e.target.value })}
                            />
                        </Field>
                        <Field id="req-websites" label="Applies to">
                            <Select<number[]>
                                id="req-websites"
                                mode="multiple"
                                style={{ width: '100%' }}
                                placeholder="Pick websites"
                                optionFilterProp="label"
                                value={draft.website_ids}
                                onChange={(value) => setDraft({ ...draft, website_ids: value })}
                                options={(websites?.items ?? []).map((w) => ({
                                    value: w.id,
                                    label: w.url,
                                }))}
                                maxTagCount="responsive"
                            />
                        </Field>
                        <div className="flex items-center gap-2">
                            <Switch
                                id="req-enabled"
                                checked={draft.enabled}
                                onChange={(enabled) => setDraft({ ...draft, enabled })}
                            />
                            <label htmlFor="req-enabled">Checked</label>
                        </div>
                    </div>
                )}
            </Modal>
        </div>
    );
}

export default Requirements;

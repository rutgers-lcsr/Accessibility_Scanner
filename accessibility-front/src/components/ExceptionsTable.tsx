'use client';
import { Field } from '@/app/websites/components/PanelFields';
import {
    ComplianceException,
    EXCEPTION_KIND_LABELS,
    EXCEPTION_STATUS_COLORS,
} from '@/lib/types/compliance';
import { useAlerts } from '@/providers/Alerts';
import { useUser } from '@/providers/User';
import { Button, Input, Modal, Popconfirm, Table, Tag } from 'antd';
import { useState } from 'react';

type Props = {
    exceptions: ComplianceException[];
    isAdmin: boolean;
    // The website's editors may withdraw their own pending requests.
    canEdit: boolean;
    showWebsite?: boolean;
    onChanged: () => void;
};

type Decision = {
    exception: ComplianceException;
    status: 'approved' | 'rejected';
    expires_on: string;
    note: string;
};

const oneYearFromNow = () => {
    const d = new Date();
    d.setFullYear(d.getFullYear() + 1);
    return d.toISOString().slice(0, 10);
};

// Exceptions with their scope, reason and decision. Site admins approve (with an expiry
// date) or reject; used on a website's Compliance tab and in the admin register.
function ExceptionsTable({ exceptions, isAdmin, canEdit, showWebsite, onChanged }: Props) {
    const { handlerUserApiRequest } = useUser();
    const { addAlert } = useAlerts();
    const [decision, setDecision] = useState<Decision | null>(null);
    const [saving, setSaving] = useState(false);

    const decide = async () => {
        if (!decision) return;
        setSaving(true);
        try {
            await handlerUserApiRequest(`/api/exceptions/${decision.exception.id}/`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    status: decision.status,
                    expires_on:
                        decision.status === 'approved' ? decision.expires_on || null : undefined,
                    decision_note: decision.note,
                }),
            });
            setDecision(null);
            onChanged();
        } catch (e) {
            addAlert('Could not save: ' + (e as Error).message, 'error');
        }
        setSaving(false);
    };

    const remove = async (id: number) => {
        try {
            await handlerUserApiRequest(`/api/exceptions/${id}/`, { method: 'DELETE' });
            onChanged();
        } catch (e) {
            addAlert('Could not delete: ' + (e as Error).message, 'error');
        }
    };

    return (
        <>
            <Table<ComplianceException>
                rowKey="id"
                dataSource={exceptions}
                pagination={{ pageSize: 20, hideOnSinglePage: true }}
                locale={{ emptyText: 'No exceptions.' }}
                columns={[
                    ...(showWebsite
                        ? [
                              {
                                  title: 'Website',
                                  key: 'website',
                                  render: (_: unknown, row: ComplianceException) => (
                                      <a
                                          href={`/websites/${row.website_id}?tab=compliance`}
                                          className="break-all"
                                      >
                                          {row.website_url}
                                      </a>
                                  ),
                              },
                          ]
                        : []),
                    {
                        title: 'Covers',
                        key: 'scope',
                        render: (_, row) => (
                            <>
                                <div>{row.rule_id ? <code>{row.rule_id}</code> : 'Every rule'}</div>
                                <div className="text-xs break-all text-gray-600">
                                    {row.url_prefix
                                        ? `Pages under ${row.url_prefix}`
                                        : 'Every page'}
                                </div>
                            </>
                        ),
                    },
                    {
                        title: 'Reason',
                        key: 'reason',
                        width: 360,
                        render: (_, row) => (
                            <>
                                <Tag>{EXCEPTION_KIND_LABELS[row.kind]}</Tag>
                                <div className="mt-1 text-sm whitespace-pre-line">{row.reason}</div>
                                <div className="text-xs text-gray-600">
                                    Requested by {row.requested_by ?? 'unknown'} on{' '}
                                    {new Date(row.requested_at).toLocaleDateString()}
                                </div>
                            </>
                        ),
                    },
                    {
                        title: 'Status',
                        key: 'status',
                        render: (_, row) => (
                            <>
                                <Tag color={EXCEPTION_STATUS_COLORS[row.status]}>{row.status}</Tag>
                                {row.expires_on && (
                                    <div className="text-xs">until {row.expires_on}</div>
                                )}
                                {row.decided_by && (
                                    <div className="text-xs text-gray-600">by {row.decided_by}</div>
                                )}
                                {row.decision_note && (
                                    <div className="text-xs">{row.decision_note}</div>
                                )}
                            </>
                        ),
                    },
                    {
                        title: '',
                        key: 'actions',
                        render: (_, row) => (
                            <div className="flex flex-wrap gap-2">
                                {isAdmin && row.status !== 'approved' && (
                                    <Button
                                        size="small"
                                        type="primary"
                                        onClick={() =>
                                            setDecision({
                                                exception: row,
                                                status: 'approved',
                                                expires_on: row.expires_on ?? oneYearFromNow(),
                                                note: row.decision_note ?? '',
                                            })
                                        }
                                    >
                                        {row.status === 'expired' ? 'Renew' : 'Approve'}
                                    </Button>
                                )}
                                {isAdmin && row.status !== 'rejected' && (
                                    <Button
                                        size="small"
                                        onClick={() =>
                                            setDecision({
                                                exception: row,
                                                status: 'rejected',
                                                expires_on: '',
                                                note: row.decision_note ?? '',
                                            })
                                        }
                                    >
                                        Reject
                                    </Button>
                                )}
                                {(isAdmin || (canEdit && row.status === 'requested')) && (
                                    <Popconfirm
                                        title={
                                            isAdmin
                                                ? 'Delete this exception?'
                                                : 'Withdraw this request?'
                                        }
                                        onConfirm={() => remove(row.id)}
                                    >
                                        <Button size="small" danger>
                                            {isAdmin ? 'Delete' : 'Withdraw'}
                                        </Button>
                                    </Popconfirm>
                                )}
                            </div>
                        ),
                    },
                ]}
            />
            <Modal
                open={decision !== null}
                title={decision?.status === 'approved' ? 'Approve exception' : 'Reject exception'}
                okText={decision?.status === 'approved' ? 'Approve' : 'Reject'}
                confirmLoading={saving}
                onOk={decide}
                onCancel={() => setDecision(null)}
            >
                {decision && (
                    <div className="space-y-4">
                        {decision.status === 'approved' && (
                            <Field
                                id="exception-expires"
                                label="Expires on"
                                help="Covered findings have no deadline until this date. Leave empty for no expiry."
                            >
                                <Input
                                    id="exception-expires"
                                    type="date"
                                    value={decision.expires_on}
                                    onChange={(e) =>
                                        setDecision({ ...decision, expires_on: e.target.value })
                                    }
                                />
                            </Field>
                        )}
                        <Field id="exception-note" label="Note">
                            <Input.TextArea
                                id="exception-note"
                                rows={3}
                                value={decision.note}
                                onChange={(e) => setDecision({ ...decision, note: e.target.value })}
                            />
                        </Field>
                    </div>
                )}
            </Modal>
        </>
    );
}

export default ExceptionsTable;

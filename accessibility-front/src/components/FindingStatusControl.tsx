'use client';
import { FINDING_STATUSES, STATUS_COLORS, STATUS_LABELS } from '@/lib/findings';
import { Finding, FindingStatus } from '@/lib/types/finding';
import { useAlerts } from '@/providers/Alerts';
import { useUser } from '@/providers/User';
import { Button, Input, Popover, Select, Tag, Tooltip } from 'antd';
import { useState } from 'react';

type Props = {
    finding: Finding;
    canEdit: boolean;
    onChanged?: (finding: Finding) => void;
};

function byLine(finding: Finding): string | null {
    if (!finding.status_at) return null;
    const when = new Date(finding.status_at).toLocaleDateString();
    return finding.status_by ? `by ${finding.status_by} on ${when}` : `by the scanner on ${when}`;
}

// A person's verdict on one finding: a status select plus an optional note. Read-only
// viewers see the status as a tag.
function FindingStatusControl({ finding, canEdit, onChanged }: Props) {
    const { handlerUserApiRequest } = useUser();
    const { addAlert } = useAlerts();
    const [saving, setSaving] = useState(false);
    const [note, setNote] = useState(finding.note ?? '');
    const [noteOpen, setNoteOpen] = useState(false);

    const save = async (status: FindingStatus, nextNote: string | null) => {
        setSaving(true);
        try {
            const updated = await handlerUserApiRequest<Finding>(`/api/findings/${finding.id}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(nextNote === null ? { status } : { status, note: nextNote }),
            });
            onChanged?.(updated);
            addAlert(`Marked as ${STATUS_LABELS[updated.status].toLowerCase()}`, 'success');
        } catch (error) {
            addAlert('Could not update the finding: ' + (error as Error).message, 'error');
        }
        setSaving(false);
    };

    const detail = byLine(finding);

    if (!canEdit) {
        if (finding.status === 'open' && !finding.note) return null;
        return (
            <Tooltip title={[detail, finding.note].filter(Boolean).join('. ') || undefined}>
                <Tag color={STATUS_COLORS[finding.status]}>{STATUS_LABELS[finding.status]}</Tag>
            </Tooltip>
        );
    }

    return (
        <span className="flex flex-wrap items-center gap-2">
            <Select
                size="small"
                style={{ minWidth: 130 }}
                aria-label="Finding status"
                value={finding.status}
                loading={saving}
                disabled={saving}
                options={FINDING_STATUSES.map((status) => ({
                    value: status,
                    label: STATUS_LABELS[status],
                }))}
                onChange={(status: FindingStatus) => save(status, null)}
            />
            <Popover
                trigger="click"
                open={noteOpen}
                onOpenChange={setNoteOpen}
                title="Note"
                content={
                    <div style={{ width: 280 }}>
                        <Input.TextArea
                            rows={3}
                            maxLength={2000}
                            value={note}
                            onChange={(e) => setNote(e.target.value)}
                            aria-label="Note on this finding"
                        />
                        <div className="mt-2 flex justify-end">
                            <Button
                                size="small"
                                type="primary"
                                loading={saving}
                                onClick={async () => {
                                    await save(finding.status, note);
                                    setNoteOpen(false);
                                }}
                            >
                                Save
                            </Button>
                        </div>
                    </div>
                }
            >
                <Button size="small" type={finding.note ? 'default' : 'dashed'}>
                    {finding.note ? 'Note' : 'Add note'}
                </Button>
            </Popover>
            {detail && <span className="text-xs text-gray-500">{detail}</span>}
        </span>
    );
}

export default FindingStatusControl;

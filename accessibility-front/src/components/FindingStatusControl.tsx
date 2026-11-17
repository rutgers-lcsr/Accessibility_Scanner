'use client';
import {
    FINDING_STATUSES,
    isSuppressed,
    REASON_MIN_LENGTH,
    STATUS_COLORS,
    STATUS_LABELS,
} from '@/lib/findings';
import { Finding, FindingStatus } from '@/lib/types/finding';
import { useAlerts } from '@/providers/Alerts';
import { useUser } from '@/providers/User';
import { Button, Input, Popover, Select, Tag, Tooltip } from 'antd';
import { useEffect, useRef, useState } from 'react';
import type { TextAreaRef } from 'antd/es/input/TextArea';

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
    // A false positive or accepted verdict waiting for its reason (required by the API).
    const [pendingStatus, setPendingStatus] = useState<FindingStatus | null>(null);
    const reasonNeeded = pendingStatus !== null;
    const reasonOk = note.trim().length >= REASON_MIN_LENGTH;
    const hasReason = (finding.note ?? '').trim().length >= REASON_MIN_LENGTH;
    // The person just chose a status that needs a reason: put them in the box for it.
    const reasonRef = useRef<TextAreaRef>(null);
    useEffect(() => {
        if (noteOpen && reasonNeeded) reasonRef.current?.focus();
    }, [noteOpen, reasonNeeded]);

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
                onChange={(status: FindingStatus) => {
                    if (isSuppressed(status) && !hasReason) {
                        setPendingStatus(status);
                        setNoteOpen(true);
                        return;
                    }
                    save(status, null);
                }}
            />
            <Popover
                trigger="click"
                open={noteOpen}
                onOpenChange={(open) => {
                    setNoteOpen(open);
                    if (!open) setPendingStatus(null);
                }}
                title={
                    reasonNeeded
                        ? `Why ${STATUS_LABELS[pendingStatus].toLowerCase()}? (required)`
                        : 'Note'
                }
                content={
                    <div style={{ width: 280 }}>
                        {reasonNeeded && (
                            <p className="text-sm text-gray-700" style={{ margin: '0 0 6px' }}>
                                It takes this element off the counts, so reviewers need the reason.
                            </p>
                        )}
                        <Input.TextArea
                            rows={3}
                            maxLength={2000}
                            value={note}
                            onChange={(e) => setNote(e.target.value)}
                            aria-label={reasonNeeded ? 'Reason (required)' : 'Note on this finding'}
                            ref={reasonRef}
                        />
                        <div className="mt-2 flex justify-end">
                            <Button
                                size="small"
                                type="primary"
                                loading={saving}
                                disabled={reasonNeeded && !reasonOk}
                                onClick={async () => {
                                    await save(pendingStatus ?? finding.status, note);
                                    setPendingStatus(null);
                                    setNoteOpen(false);
                                }}
                            >
                                {reasonNeeded
                                    ? `Mark ${STATUS_LABELS[pendingStatus].toLowerCase()}`
                                    : 'Save'}
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

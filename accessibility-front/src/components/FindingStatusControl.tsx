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
import { Button, Input, Modal, Select, Tag, Tooltip } from 'antd';
import { useRef, useState } from 'react';
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
    // Focus goes back to whatever opened the dialog: the status menu or the note button.
    const returnTo = useRef<HTMLElement | null>(null);
    const openNote = () => {
        returnTo.current = document.activeElement as HTMLElement | null;
        setNoteOpen(true);
    };
    const closeNote = () => {
        setNoteOpen(false);
        setPendingStatus(null);
    };

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
                        openNote();
                        return;
                    }
                    save(status, null);
                }}
            />
            {/* A dialog, not a popover: it takes focus, closes on Escape and returns focus. */}
            <Button
                size="small"
                type={finding.note ? 'default' : 'dashed'}
                aria-haspopup="dialog"
                onClick={openNote}
            >
                {finding.note ? 'Note' : 'Add note'}
            </Button>
            <Modal
                open={noteOpen}
                title={
                    reasonNeeded
                        ? `Why ${STATUS_LABELS[pendingStatus].toLowerCase()}? (required)`
                        : 'Note on this element'
                }
                okText={
                    reasonNeeded ? `Mark ${STATUS_LABELS[pendingStatus].toLowerCase()}` : 'Save'
                }
                okButtonProps={{ disabled: reasonNeeded && !reasonOk, loading: saving }}
                onOk={async () => {
                    await save(pendingStatus ?? finding.status, note);
                    closeNote();
                }}
                onCancel={closeNote}
                afterOpenChange={(open) => {
                    if (open) reasonRef.current?.focus();
                }}
                afterClose={() => returnTo.current?.focus()}
            >
                {reasonNeeded && (
                    <p style={{ margin: '0 0 8px' }}>
                        It takes this element off every count, so reviewers need the reason (at
                        least {REASON_MIN_LENGTH} characters).
                    </p>
                )}
                <Input.TextArea
                    rows={3}
                    maxLength={2000}
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    aria-label={reasonNeeded ? 'Reason (required)' : 'Note on this element'}
                    aria-required={reasonNeeded}
                    ref={reasonRef}
                />
            </Modal>
            {detail && <span className="text-xs text-gray-500">{detail}</span>}
        </span>
    );
}

export default FindingStatusControl;

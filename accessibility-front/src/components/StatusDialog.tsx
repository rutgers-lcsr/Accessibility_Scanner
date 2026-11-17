'use client';
import { isSuppressed, REASON_MIN_LENGTH, STATUS_LABELS } from '@/lib/findings';
import { FindingStatus } from '@/lib/types/finding';
import { Input, Modal, Radio } from 'antd';
import { useId, useState } from 'react';

// What each status means, said where the choice is made.
const STATUS_HINTS: Record<FindingStatus, string> = {
    open: 'still to fix',
    fixed: 'changed on the site; the next scan confirms it',
    false_positive: 'the check is wrong about these elements',
    accepted: 'known, and will not be fixed',
};

type Props = {
    open: boolean;
    // How many elements the choice applies to, and where ("On every page of this website.").
    count: number;
    title: string;
    scope: string;
    onCancel: () => void;
    onConfirm: (status: FindingStatus, note?: string) => void;
};

// One decision for many elements: the status (nothing chosen at first, so a stray Enter
// changes nothing), each status explained, and a reason when the status hides elements
// from the counts. A dialog: it takes focus, closes on Escape and gives focus back.
export default function StatusDialog({ open, count, title, scope, onCancel, onConfirm }: Props) {
    const id = useId();
    const [choice, setChoice] = useState<FindingStatus | null>(null);
    const [reason, setReason] = useState('');
    const needsReason = choice !== null && isSuppressed(choice);
    const blocked =
        choice === null
            ? 'Choose a status.'
            : needsReason && !reason.trim()
              ? `Add a reason of at least ${REASON_MIN_LENGTH} characters.`
              : needsReason && reason.trim().length < REASON_MIN_LENGTH
                ? `The reason needs at least ${REASON_MIN_LENGTH} characters.`
                : null;
    const reset = () => {
        setChoice(null);
        setReason('');
    };

    return (
        <Modal
            open={open}
            title={title}
            okText={
                choice ? `Mark ${count} as ${STATUS_LABELS[choice].toLowerCase()}` : 'Mark them'
            }
            okButtonProps={{ disabled: blocked !== null }}
            onOk={() => {
                if (!choice) return;
                const note = isSuppressed(choice) ? reason.trim() : undefined;
                reset();
                onConfirm(choice, note);
            }}
            onCancel={() => {
                reset();
                onCancel();
            }}
        >
            <p className="text-sm text-gray-700" style={{ margin: '0 0 12px' }}>
                {scope}
            </p>
            <Radio.Group
                value={choice}
                onChange={(e) => setChoice(e.target.value as FindingStatus)}
                aria-label="Status"
                style={{ display: 'flex', flexDirection: 'column', gap: 6 }}
            >
                {(Object.keys(STATUS_LABELS) as FindingStatus[]).map((status) => (
                    <Radio key={status} value={status}>
                        {STATUS_LABELS[status]}
                        {/* Read as "Open, still to fix", not run together. */}
                        <span className="sr-only">,</span>
                        <span className="ml-2 text-sm text-gray-600">{STATUS_HINTS[status]}</span>
                    </Radio>
                ))}
            </Radio.Group>
            {needsReason && (
                <div style={{ marginTop: 16 }}>
                    <p id={`${id}-why`} style={{ margin: '0 0 8px' }}>
                        They will no longer count in this website&apos;s totals, Fix first or the
                        dashboard. Reviewers see who marked them and why.
                    </p>
                    <label htmlFor={`${id}-reason`} className="text-sm font-medium">
                        Reason (required, at least {REASON_MIN_LENGTH} characters)
                    </label>
                    <Input.TextArea
                        id={`${id}-reason`}
                        rows={3}
                        maxLength={2000}
                        value={reason}
                        aria-required
                        aria-describedby={`${id}-why`}
                        onChange={(e) => setReason(e.target.value)}
                        style={{ marginTop: 4 }}
                    />
                </div>
            )}
            {/* Why the confirm button is off, said instead of left to guess. */}
            <output className="mt-3 block text-sm text-gray-700">{blocked}</output>
        </Modal>
    );
}

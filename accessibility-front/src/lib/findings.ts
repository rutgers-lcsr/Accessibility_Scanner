import { FindingStatus } from '@/lib/types/finding';

export const FINDING_STATUSES: FindingStatus[] = ['open', 'fixed', 'false_positive', 'accepted'];

export const STATUS_LABELS: Record<FindingStatus, string> = {
    open: 'Open',
    fixed: 'Fixed',
    false_positive: 'False positive',
    accepted: 'Accepted',
};

// antd Tag colours; the label is always shown next to them.
export const STATUS_COLORS: Record<FindingStatus, string> = {
    open: 'default',
    fixed: 'green',
    false_positive: 'purple',
    accepted: 'blue',
};

// False positive and accepted need a reason this long (services.findings.REASON_MIN_LENGTH).
export const REASON_MIN_LENGTH = 10;

export function isSuppressed(status: FindingStatus): boolean {
    return status === 'false_positive' || status === 'accepted';
}

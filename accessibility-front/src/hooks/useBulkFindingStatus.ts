'use client';
import { FindingStatus } from '@/lib/types/finding';
import { useAlerts } from '@/providers/Alerts';
import { useUser } from '@/providers/User';

// "Mark all on this website as…" for one rule; `onDone` refreshes whatever showed the counts.
export function useBulkFindingStatus(websiteId: number, onDone?: () => Promise<void> | void) {
    const { handlerUserApiRequest } = useUser();
    const { addAlert } = useAlerts();
    return async (ruleId: string, status: FindingStatus) => {
        try {
            const result = await handlerUserApiRequest<{ updated: number }>(
                `/api/websites/${websiteId}/findings/bulk`,
                {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ rule_id: ruleId, status }),
                }
            );
            addAlert(`${result.updated} elements of ${ruleId} marked`, 'success');
            await onDone?.();
        } catch (error) {
            addAlert('Could not update the findings: ' + (error as Error).message, 'error');
        }
    };
}

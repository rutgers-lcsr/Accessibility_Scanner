'use client';
import ViolationsList from '@/components/ViolationsList';
import { fetcherApi } from '@/lib/api';
import { WebsiteAxeReport } from '@/lib/types/axe';
import { FindingRuleGroup, FindingStatus, WebsiteFindings } from '@/lib/types/finding';
import { PublicUser } from '@/lib/types/user';
import { useAlerts } from '@/providers/Alerts';
import { useUser } from '@/providers/User';
import { Card } from 'antd';
import useSWR from 'swr';

type Props = {
    websiteId: number;
    report: WebsiteAxeReport;
    user: PublicUser | null;
    canEdit: boolean;
    // Refresh the website (header counts) after a verdict changed what counts.
    onCountsChanged?: () => void;
};

function WebsiteReport({ websiteId, report, user, canEdit, onCountsChanged }: Props) {
    const { handlerUserApiRequest } = useUser();
    const { addAlert } = useAlerts();
    const { data: findings, mutate } = useSWR<WebsiteFindings>(
        `/api/websites/${websiteId}/findings?status=current`,
        user ? handlerUserApiRequest<WebsiteFindings> : fetcherApi<WebsiteFindings>
    );

    if (!report) return <div>No report data available.</div>;

    if (!report.violations || report.violations.length === 0)
        return (
            <div className="mt-2">
                <Card title="Accessibility Violations">
                    <div className="text-center text-green-600">
                        No accessibility violations found.
                    </div>
                </Card>
            </div>
        );

    const pages = Array.from(
        new Set(report.violations.flatMap((v) => v.reports.map((r) => r.url)))
    ).sort();
    const ruleFindings: Record<string, FindingRuleGroup> = {};
    for (const group of findings?.rules ?? []) ruleFindings[group.rule_id] = group;

    const onBulkStatus = async (ruleId: string, status: FindingStatus) => {
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
            await mutate();
            onCountsChanged?.();
        } catch (error) {
            addAlert('Could not update the findings: ' + (error as Error).message, 'error');
        }
    };

    return (
        <div className="mt-2">
            <Card
                title={<span className="font-semibold text-lg">Accessibility Violations</span>}
                styles={{ body: { paddingTop: 16, paddingBottom: 16 } }}
            >
                <ViolationsList
                    violations={report.violations}
                    pages={pages}
                    ruleFindings={findings ? ruleFindings : undefined}
                    canEdit={canEdit}
                    onBulkStatus={onBulkStatus}
                />
            </Card>
        </div>
    );
}

export default WebsiteReport;

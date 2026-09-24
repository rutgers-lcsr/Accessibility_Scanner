'use client';
import RuleRows from '@/app/websites/components/RuleRows';
import ScanProgressModal from '@/components/ScanProgressModal';
import { useScan } from '@/hooks/useScan';
import { WebsiteChanges } from '@/lib/types/finding';
import { useUser } from '@/providers/User';
import { Alert, Button, Collapse, Spin } from 'antd';
import { useState } from 'react';

type Summary = { reportId: number | null; changes: WebsiteChanges };

type Props = {
    siteId: number;
    size?: 'small' | 'middle';
    // After the scan finished and was compared with the previous one.
    onScanned?: (reportId: number | null, changes: WebsiteChanges) => void;
};

const plural = (count: number, noun: string) => `${count} ${noun}${count === 1 ? '' : 's'}`;

// What a page rescan changed: fixed, still open and new, from the page's latest report
// against its previous one.
export function VerifySummary({ reportId, changes }: Summary) {
    const first = changes.since === null;
    const stillOpen = changes.still_open.reduce((n, rule) => n + rule.count, 0);
    const type = changes.regression
        ? 'warning'
        : changes.fixed_count > 0 && changes.new_count === 0
          ? 'success'
          : 'info';
    const headline = first
        ? `First scan of this page: ${plural(changes.open_count, 'open issue')}`
        : `Fixed ${changes.fixed_count}, still open ${stillOpen}, new ${changes.new_count}` +
          (changes.reopened_count ? ` (${changes.reopened_count} reopened)` : '');
    return (
        <div aria-live="polite">
            <Alert
                type={type}
                showIcon
                title={headline}
                description={
                    <>
                        {changes.regression && <p>This scan is worse than the previous one.</p>}
                        <p className="text-xs text-gray-600">
                            This rescan is now the page&apos;s latest report: the website&apos;s
                            &quot;What changed&quot; tab and the next email compare against it.
                        </p>
                        {reportId !== null && (
                            <a href={`/reports/${reportId}`}>Open the new report</a>
                        )}
                    </>
                }
            />
            {!first && (
                <Collapse
                    className="mt-3"
                    items={[
                        {
                            key: 'fixed',
                            label: `Fixed (${changes.fixed_count})`,
                            children: <RuleRows rules={changes.fixed} empty="Nothing fixed." />,
                        },
                        {
                            key: 'open',
                            label: `Still open (${stillOpen})`,
                            children: (
                                <RuleRows rules={changes.still_open} empty="Nothing left open." />
                            ),
                        },
                        {
                            key: 'new',
                            label: `New (${changes.new_count})`,
                            children: <RuleRows rules={changes.new} empty="Nothing new." />,
                        },
                    ]}
                />
            )}
        </div>
    );
}

// Rescan one page and show what got fixed. The scan runs on its own queue, so it does
// not wait behind a website crawl.
function RescanPageButton({ siteId, size = 'middle', onScanned }: Props) {
    const { handlerUserApiRequest } = useUser();
    const [summary, setSummary] = useState<Summary | null>(null);
    const {
        loading,
        taskId,
        statusEndpoint,
        showProgress,
        startScan,
        handleScanComplete,
        handleScanError,
        handleCloseProgress,
    } = useScan({
        siteId,
        closeOnComplete: false,
        onComplete: async (status) => {
            const reportId = status?.result?.report_id ?? null;
            try {
                const changes = await handlerUserApiRequest<WebsiteChanges>(
                    `/api/sites/${siteId}/changes`
                );
                setSummary({ reportId, changes });
                onScanned?.(reportId, changes);
            } catch {
                setSummary(null);
            }
        },
    });

    return (
        <>
            <Button
                size={size}
                loading={loading}
                aria-busy={loading}
                onClick={() => {
                    setSummary(null);
                    startScan();
                }}
            >
                Rescan this page
            </Button>
            {taskId && statusEndpoint && (
                <ScanProgressModal
                    taskId={taskId}
                    statusEndpoint={statusEndpoint}
                    onComplete={handleScanComplete}
                    onError={handleScanError}
                    visible={showProgress}
                    onClose={handleCloseProgress}
                    renderSuccess={() =>
                        summary ? (
                            <VerifySummary reportId={summary.reportId} changes={summary.changes} />
                        ) : (
                            <Spin aria-label="Comparing with the previous scan" />
                        )
                    }
                />
            )}
        </>
    );
}

export default RescanPageButton;

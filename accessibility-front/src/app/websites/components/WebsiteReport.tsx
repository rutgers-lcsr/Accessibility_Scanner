'use client';
import ViolationsList from '@/components/ViolationsList';
import { useBulkFindingStatus } from '@/hooks/useBulkFindingStatus';
import { fetcherApi } from '@/lib/api';
import { WebsiteAxeReport } from '@/lib/types/axe';
import { FindingRuleGroup, WebsiteFindings } from '@/lib/types/finding';
import { PublicUser } from '@/lib/types/user';
import { useUser } from '@/providers/User';
import AuditAccessibilityItem from '@/components/AuditAccessibilityItem';
import { Alert } from 'antd';
import { useEffect } from 'react';
import useSWR from 'swr';

type Props = {
    websiteId: number;
    report: WebsiteAxeReport;
    user: PublicUser | null;
    canEdit: boolean;
    // Refresh the website (header counts) after a verdict changed what counts.
    onCountsChanged?: () => void;
    canScan?: boolean;
    onPageScanned?: () => void;
};

function WebsiteReport({
    websiteId,
    report,
    user,
    canEdit,
    onCountsChanged,
    canScan,
    onPageScanned,
}: Props) {
    const { handlerUserApiRequest } = useUser();
    const { data: findings, mutate } = useSWR<WebsiteFindings>(
        `/api/websites/${websiteId}/findings?status=current`,
        user ? handlerUserApiRequest<WebsiteFindings> : fetcherApi<WebsiteFindings>
    );

    // Before any early return: a rescan that clears every violation must not change the
    // number of hooks this component calls.
    const onBulkStatus = useBulkFindingStatus(websiteId, async () => {
        await mutate();
        onCountsChanged?.();
    });

    // The summary and its tiles link here (?tab=violations#needs-review, #issues-by-rule)
    // before this tab has rendered, so the browser's own jump to the hash finds nothing;
    // jump once the section is on the page.
    useEffect(() => {
        const hash = window.location.hash;
        if (hash === '#needs-review' || hash === '#issues-by-rule')
            document.getElementById(hash.slice(1))?.scrollIntoView({ block: 'start' });
    }, [report]);

    if (!report) return <div>No report data available.</div>;

    const toCheck = report.incomplete ?? [];
    const failing = new Set((report.violations ?? []).map((v) => v.id));
    const needsReview = toCheck.length > 0 && (
        <section aria-labelledby="needs-review" className="mt-8">
            <h2 id="needs-review" className="mb-1 text-xl font-semibold">
                Needs a manual check ({toCheck.length})
            </h2>
            <p className="mb-4 max-w-[75ch] text-gray-700">
                The automated checks could not decide these, often because of a background image or
                hidden content. Open a page to look at each element, and fix it if the problem
                applies. They do not count towards the issues above. A rule can be in both lists:
                some of its elements failed, others could not be decided.
            </p>
            {toCheck.map((result) => (
                <AuditAccessibilityItem
                    key={result.id}
                    accessibilityResult={result}
                    idPrefix="review"
                    note={
                        failing.has(result.id)
                            ? 'This rule also failed on other elements, listed above. These are different elements the scan could not decide.'
                            : undefined
                    }
                    nodeLabel="Example elements to check (from the first page)"
                />
            ))}
        </section>
    );

    if (!report.violations || report.violations.length === 0)
        return (
            <div className="mt-2">
                <Alert
                    type="success"
                    showIcon
                    title="No element failed an automated check on this website."
                />
                {needsReview}
            </div>
        );

    const pages = Array.from(
        new Set(report.violations.flatMap((v) => v.reports.map((r) => r.url)))
    ).sort();
    const ruleFindings: Record<string, FindingRuleGroup> = {};
    for (const group of findings?.rules ?? []) ruleFindings[group.rule_id] = group;

    return (
        <div className="mt-2">
            <h2 id="issues-by-rule" className="sr-only">
                Issues by rule
            </h2>
            <ViolationsList
                violations={report.violations}
                pages={pages}
                ruleFindings={findings ? ruleFindings : undefined}
                canEdit={canEdit}
                onBulkStatus={onBulkStatus}
                canScan={canScan}
                onPageScanned={onPageScanned}
            />
            {needsReview}
        </div>
    );
}

export default WebsiteReport;

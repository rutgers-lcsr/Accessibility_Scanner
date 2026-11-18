'use client';
import PageLoading from '@/components/PageLoading';
import { fetcherApi } from '@/lib/api';
import { STATUS_LABELS } from '@/lib/findings';
import { Finding, FindingStatus, WebsiteFindings } from '@/lib/types/finding';
import { PublicUser } from '@/lib/types/user';
import { useUser } from '@/providers/User';
import { Drawer, Tag } from 'antd';
import { useState } from 'react';
import useSWR from 'swr';

type Change = {
    old_status: FindingStatus | null;
    new_status: FindingStatus;
    note: string | null;
    by: string | null;
    scope: 'element' | 'group' | 'rule';
    batch_size: number;
    at: string | null;
};

const day = (iso: string | null) =>
    iso ? new Date(iso).toLocaleDateString(undefined, { dateStyle: 'medium' }) : 'an unknown date';

const SCOPE: Record<Change['scope'], string> = {
    element: 'this element alone',
    group: 'a group of',
    rule: 'every element of the rule,',
};

// Every status a person gave one finding, loaded when opened (backend status history).
function History({ findingId, user }: { findingId: number; user: PublicUser | null }) {
    const { handlerUserApiRequest } = useUser();
    const { data, error } = useSWR(
        `/api/findings/${findingId}/history/`,
        user ? handlerUserApiRequest<{ changes: Change[] }> : fetcherApi<{ changes: Change[] }>
    );
    if (error) return <p className="m-0 text-sm">Could not load the history.</p>;
    if (!data) return <PageLoading minimal />;
    if (!data.changes.length) return <p className="m-0 text-sm">No changes recorded.</p>;
    return (
        <ol className="m-0 list-decimal pl-5 text-sm">
            {data.changes.map((change, index) => (
                <li key={index}>
                    {day(change.at)}: {change.by ?? 'the scanner'} set{' '}
                    <strong>{STATUS_LABELS[change.new_status]}</strong>
                    {change.old_status && (
                        <> (was {STATUS_LABELS[change.old_status].toLowerCase()})</>
                    )}
                    {change.scope !== 'element' && (
                        <>
                            {' '}
                            for {SCOPE[change.scope]} {change.batch_size} element
                            {change.batch_size === 1 ? '' : 's'} at once
                        </>
                    )}
                    {change.note && <>: “{change.note}”</>}
                </li>
            ))}
        </ol>
    );
}

type Props = {
    websiteId: number;
    user: PublicUser | null;
    open: boolean;
    onClose: () => void;
};

// The elements left out of the website's counts (false positive or accepted), each with
// who marked it, when and why, and its full history: what a reviewer checks before
// trusting the totals.
export default function SuppressedElements({ websiteId, user, open, onClose }: Props) {
    const { handlerUserApiRequest } = useUser();
    const { data, error } = useSWR(
        open ? `/api/websites/${websiteId}/findings/?status=suppressed` : null,
        user ? handlerUserApiRequest<WebsiteFindings> : fetcherApi<WebsiteFindings>
    );
    const [shown, setShown] = useState<Set<number>>(new Set());

    // Only elements in each page's latest scan: the ones the counts leave out now.
    const rows: { finding: Finding; url: string; reportId: number | null; help: string }[] = [];
    for (const rule of data?.rules ?? []) {
        for (const page of rule.pages) {
            for (const finding of page.findings) {
                if (finding.last_report_id === page.report_id) {
                    rows.push({
                        finding,
                        url: page.url,
                        reportId: page.report_id,
                        help: rule.help ?? rule.rule_id,
                    });
                }
            }
        }
    }

    return (
        <Drawer open={open} onClose={onClose} title="Elements not counted" size="large">
            {error && <p>Could not load the elements.</p>}
            {!data && !error && <PageLoading minimal />}
            {data && (
                <>
                    <p className="mt-0 text-sm text-gray-700">
                        {rows.length} element{rows.length === 1 ? '' : 's'} marked false positive or
                        accepted, left out of this website&apos;s counts, Fix first and the
                        dashboard. Each shows who marked it and why; open its history for every
                        change.
                    </p>
                    <ul className="m-0 list-none space-y-3 p-0">
                        {rows.map(({ finding, url, reportId, help }) => (
                            <li
                                key={finding.id}
                                className="rounded border border-gray-200 p-3 text-sm"
                            >
                                <div className="flex flex-wrap items-center gap-2">
                                    <Tag color="gold">{STATUS_LABELS[finding.status]}</Tag>
                                    <span className="font-medium">{help}</span>
                                </div>
                                <p className="mb-1 mt-2">
                                    {reportId ? (
                                        <a className="underline" href={`/reports/${reportId}`}>
                                            {url}
                                        </a>
                                    ) : (
                                        url
                                    )}
                                    {finding.selector && (
                                        <>
                                            {' · '}
                                            <code className="break-all">{finding.selector}</code>
                                        </>
                                    )}
                                </p>
                                <p className="m-0">
                                    Marked by {finding.status_by ?? 'an unknown person'} on{' '}
                                    {day(finding.status_at)}
                                    {finding.note ? (
                                        <>: “{finding.note}”</>
                                    ) : (
                                        ' with no reason given'
                                    )}
                                </p>
                                <details
                                    className="mt-2"
                                    onToggle={(e) => {
                                        if ((e.target as HTMLDetailsElement).open)
                                            setShown((prev) => new Set(prev).add(finding.id));
                                    }}
                                >
                                    <summary className="cursor-pointer text-xs text-gray-700">
                                        History of this element&apos;s status
                                    </summary>
                                    <div className="mt-2">
                                        {shown.has(finding.id) && (
                                            <History findingId={finding.id} user={user} />
                                        )}
                                    </div>
                                </details>
                            </li>
                        ))}
                    </ul>
                </>
            )}
        </Drawer>
    );
}

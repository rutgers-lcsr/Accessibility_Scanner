'use client';
import { STATUS_COLORS, STATUS_LABELS } from '@/lib/findings';
import { ImpactTag } from '@/lib/impact';
import { AxeNode, AxeResult, WebsiteAxeResult } from '@/lib/types/axe';
import { Finding, FindingRuleGroup, FindingStatus } from '@/lib/types/finding';
import { Button, Card, Collapse, Tag, Tooltip } from 'antd';
import { useState } from 'react';
import { useGuides } from '@/hooks/useGuides';
import { guideHref } from '@/lib/guides';
import RescanPageButton from './RescanPageButton';
import StatusDialog from './StatusDialog';
import { parseContrast, plainContrastFix } from '@/lib/contrast';
import { signature } from '@/lib/signature';
import ViolationNode, { findingKey, findingSelector } from './ViolationNode';

type Props = {
    accessibilityResult: WebsiteAxeResult | AxeResult;
    // Offer "Show in preview" on each element (the report page, where the preview iframe is).
    previewEnabled?: boolean;
    // Findings of this page's latest report, keyed by findingKey (report page).
    findingsBySelector?: Map<string, Finding>;
    // Current findings of this rule across the website (website page).
    ruleFindings?: FindingRuleGroup;
    canEdit?: boolean;
    onFindingChanged?: (finding: Finding) => void;
    onBulkStatus?: (ruleId: string, status: FindingStatus, note?: string) => Promise<void>;
    canScan?: boolean;
    onPageScanned?: () => void;
    // Anchor prefix of the card: "violation" (#violation-<rule>), or "review" for the
    // needs-a-manual-check list, which can hold the same rule ids.
    idPrefix?: string;
    // What the element list is called ("Elements", "Elements to check").
    nodeLabel?: string;
    // A line under the description, e.g. that the same rule also failed elsewhere.
    note?: string;
    // Opens every element of this rule (website page), from the card's actions.
    onShowAll?: (opener: HTMLElement) => void;
};

const NODE_PAGE = 10;

function isWebsiteResult(result: WebsiteAxeResult | AxeResult): result is WebsiteAxeResult {
    return (result as WebsiteAxeResult).reports !== undefined;
}

// One group's elements, ten at a time, without repeating the group's fix sentence.
function GroupNodes({
    ruleId,
    nodes,
    previewEnabled,
    findingsBySelector,
    canEdit,
    onFindingChanged,
}: {
    ruleId: string;
    nodes: AxeNode[];
    previewEnabled?: boolean;
    findingsBySelector?: Map<string, Finding>;
    canEdit?: boolean;
    onFindingChanged?: (finding: Finding) => void;
}) {
    const [shown, setShown] = useState(NODE_PAGE);
    return (
        <>
            <ul style={{ paddingLeft: 0, margin: 0, listStyle: 'none' }}>
                {nodes.slice(0, shown).map((node, idx) => (
                    <ViolationNode
                        key={idx}
                        node={node}
                        grouped
                        previewEnabled={previewEnabled}
                        finding={findingsBySelector?.get(findingKey(ruleId, findingSelector(node)))}
                        canEdit={canEdit}
                        onFindingChanged={onFindingChanged}
                    />
                ))}
            </ul>
            {shown < nodes.length && (
                <Button size="small" onClick={() => setShown(nodes.length)}>
                    Show all {nodes.length}
                </Button>
            )}
        </>
    );
}

// A rule's failing elements, ten at a time so a rule with hundreds stays cheap to open.
function NodeList({
    ruleId,
    nodes,
    label,
    open,
    previewEnabled,
    findingsBySelector,
    canEdit,
    onFindingChanged,
}: {
    ruleId: string;
    nodes: AxeNode[];
    label: string;
    open: boolean;
    previewEnabled?: boolean;
    findingsBySelector?: Map<string, Finding>;
    canEdit?: boolean;
    onFindingChanged?: (finding: Finding) => void;
}) {
    const [shown, setShown] = useState(NODE_PAGE);
    // Group by shared markup when it repeats (lib/signature, as the website drawer does).
    const byMarkup = new Map<string, AxeNode[]>();
    for (const node of nodes) {
        const key = signature(node.html, node.failureSummary);
        byMarkup.set(key, [...(byMarkup.get(key) ?? []), node]);
    }
    const groups = [...byMarkup.entries()].sort((x, y) => y[1].length - x[1].length);
    const grouped = nodes.length >= 4 && groups.length < nodes.length;
    return (
        <Collapse
            defaultActiveKey={open ? ['nodes'] : []}
            items={[
                {
                    key: 'nodes',
                    label: (
                        <span className="font-medium">
                            {label}
                            <Tag color="blue" style={{ marginLeft: 8 }}>
                                {nodes.length}
                            </Tag>
                        </span>
                    ),
                    children: grouped ? (
                        // Repeated markup on one page (a code theme's 36 tokens): one group,
                        // one fix sentence, instead of 36 identical cards.
                        <div className="flex flex-col gap-4">
                            {groups.map(([label, members]) => {
                                const first = members[0];
                                const colours = parseContrast(first.failureSummary);
                                const fix = plainContrastFix(first.failureSummary, {
                                    html: first.html,
                                    selector: findingSelector(first),
                                });
                                return (
                                    <section
                                        key={label}
                                        aria-label={`${members.length} element${members.length === 1 ? '' : 's'}: ${label}`}
                                    >
                                        <div className="mb-2 flex flex-wrap items-center gap-x-3 gap-y-1">
                                            {colours && (
                                                <span
                                                    aria-hidden="true"
                                                    className="inline-flex overflow-hidden rounded border border-gray-300"
                                                >
                                                    <span
                                                        className="h-4 w-4"
                                                        style={{ background: colours.foreground }}
                                                    />
                                                    <span
                                                        className="h-4 w-4"
                                                        style={{ background: colours.background }}
                                                    />
                                                </span>
                                            )}
                                            <code className="text-sm">{label}</code>
                                            <Tag>
                                                {members.length} element
                                                {members.length === 1 ? '' : 's'}
                                            </Tag>
                                        </div>
                                        {fix && (
                                            <p
                                                className="font-medium text-gray-900"
                                                style={{ margin: '0 0 8px' }}
                                            >
                                                {fix}
                                            </p>
                                        )}
                                        <GroupNodes
                                            ruleId={ruleId}
                                            nodes={members}
                                            previewEnabled={previewEnabled}
                                            findingsBySelector={findingsBySelector}
                                            canEdit={canEdit}
                                            onFindingChanged={onFindingChanged}
                                        />
                                    </section>
                                );
                            })}
                        </div>
                    ) : (
                        <>
                            <ul style={{ paddingLeft: 0, margin: 0, listStyle: 'none' }}>
                                {nodes.slice(0, shown).map((node, idx) => (
                                    <ViolationNode
                                        key={idx}
                                        node={node}
                                        previewEnabled={previewEnabled}
                                        finding={findingsBySelector?.get(
                                            findingKey(ruleId, findingSelector(node))
                                        )}
                                        canEdit={canEdit}
                                        onFindingChanged={onFindingChanged}
                                    />
                                ))}
                            </ul>
                            {shown < nodes.length && (
                                <div className="flex gap-2">
                                    <Button
                                        size="small"
                                        onClick={() => setShown(shown + NODE_PAGE)}
                                    >
                                        Show {Math.min(NODE_PAGE, nodes.length - shown)} more
                                    </Button>
                                    <Button
                                        size="small"
                                        type="link"
                                        onClick={() => setShown(nodes.length)}
                                    >
                                        Show all {nodes.length}
                                    </Button>
                                </div>
                            )}
                        </>
                    ),
                },
            ]}
        />
    );
}

// Status counts of a rule's current findings across the website, plus a bulk verdict menu.
export function RuleFindingsSummary({
    ruleId,
    group,
    canEdit,
    onBulkStatus,
}: {
    ruleId: string;
    group: Pick<FindingRuleGroup, 'counts'>;
    canEdit?: boolean;
    onBulkStatus?: (ruleId: string, status: FindingStatus, note?: string) => Promise<void>;
}) {
    const [busy, setBusy] = useState(false);
    const [open, setOpen] = useState(false);
    const total = Object.values(group.counts).reduce((sum, n) => sum + n, 0);
    const suppressed = group.counts.false_positive + group.counts.accepted;
    return (
        <div className="mt-3 flex flex-wrap items-center gap-2">
            {(Object.keys(STATUS_LABELS) as FindingStatus[])
                .filter((status) => group.counts[status] > 0)
                .map((status) => (
                    <Tag key={status} color={STATUS_COLORS[status]}>
                        {STATUS_LABELS[status]}: {group.counts[status]}
                    </Tag>
                ))}
            {group.counts.open === 0 && suppressed > 0 && (
                <Tooltip title="Every current element of this rule is marked false positive or accepted, so it no longer counts.">
                    <Tag color="gold">Suppressed</Tag>
                </Tooltip>
            )}
            {canEdit && onBulkStatus && (
                <>
                    <Button
                        size="small"
                        loading={busy}
                        aria-haspopup="dialog"
                        aria-label={`Set the status of all ${total} elements of rule ${ruleId} on this website`}
                        onClick={() => setOpen(true)}
                    >
                        Set status for all {total}…
                    </Button>
                    <StatusDialog
                        open={open}
                        count={total}
                        title={`Status for all ${total} element${total === 1 ? '' : 's'} of this rule`}
                        scope="On every page of this website."
                        onCancel={() => setOpen(false)}
                        onConfirm={async (status, note) => {
                            setOpen(false);
                            setBusy(true);
                            await onBulkStatus(ruleId, status, note);
                            setBusy(false);
                        }}
                    />
                </>
            )}
        </div>
    );
}

function AuditAccessibilityItem({
    accessibilityResult,
    previewEnabled = false,
    findingsBySelector,
    ruleFindings,
    canEdit = false,
    onFindingChanged,
    onBulkStatus,
    canScan = false,
    onPageScanned,
    idPrefix = 'violation',
    nodeLabel,
    note,
    onShowAll,
}: Props) {
    const guides = useGuides();
    if (!accessibilityResult) return <div>No accessibility result provided.</div>;

    const ruleId = accessibilityResult.id;
    const cardId = `${idPrefix}-${ruleId}`;
    // The same card on the website page and the page report: the plain-language rule as
    // the title, what it means, one "How to fix" (our guide when there is one, else
    // Deque's page), and the rule id and standards out of the way.
    const title = (
        <h3 className="text-base font-semibold whitespace-normal md:text-lg" style={{ margin: 0 }}>
            {accessibilityResult.help || ruleId}
        </h3>
    );
    // A rule to check by hand has not failed, so it does not wear a severity colour.
    const badge =
        idPrefix === 'review' ? (
            <Tag>Check by hand</Tag>
        ) : (
            <ImpactTag impact={accessibilityResult.impact} />
        );
    const header = (
        <>
            <p className="mb-2 text-gray-700">{accessibilityResult.description}</p>
            {note && <p className="mb-2 text-sm font-medium text-gray-800">{note}</p>}
        </>
    );
    const hasGuide = guides.has(ruleId);
    const footer = (
        <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2">
            {hasGuide ? (
                <Button type="primary" href={guideHref(ruleId)}>
                    How to fix
                </Button>
            ) : (
                <Button
                    type="primary"
                    href={accessibilityResult.helpUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                >
                    How to fix
                </Button>
            )}
            {onShowAll && (
                <Button aria-haspopup="dialog" onClick={(e) => onShowAll(e.currentTarget)}>
                    Every element of this rule
                </Button>
            )}
            {hasGuide && (
                <a href={accessibilityResult.helpUrl} target="_blank" rel="noopener noreferrer">
                    More detail (Deque)
                </a>
            )}
            <details className="text-sm text-gray-600">
                <summary className="cursor-pointer">Technical details</summary>
                <p className="mt-2 mb-1">
                    Rule <code>{ruleId}</code>
                </p>
                {!!accessibilityResult.tags?.length && (
                    <div className="flex flex-wrap gap-1">
                        {accessibilityResult.tags.map((tag) => (
                            <Tag key={tag}>{tag}</Tag>
                        ))}
                    </div>
                )}
            </details>
        </div>
    );

    if (isWebsiteResult(accessibilityResult)) {
        const reportItems: Parameters<typeof Collapse>[0]['items'] = [
            {
                key: 'pages',
                label: (
                    <span className="font-medium">
                        Pages with this issue
                        <Tag color="blue" style={{ marginLeft: 8 }}>
                            {accessibilityResult.reports.length}
                        </Tag>
                    </span>
                ),
                children: (
                    <ul style={{ paddingLeft: 0, margin: 0 }}>
                        {/* Most elements first: the page to start on. */}
                        {[...accessibilityResult.reports]
                            .sort((a, b) => (b.node_count ?? 0) - (a.node_count ?? 0))
                            .map((report, idx) => (
                                <li
                                    key={idx}
                                    style={{
                                        listStyle: 'none',
                                        marginBottom: 12,
                                        display: 'flex',
                                        alignItems: 'center',
                                    }}
                                >
                                    <Tag color="geekblue" style={{ marginRight: 8 }}>
                                        {new Date(report.timestamp).toLocaleString()}
                                    </Tag>
                                    {report.node_count !== undefined && (
                                        <Tag style={{ marginRight: 8 }}>
                                            {report.node_count}{' '}
                                            {report.node_count === 1 ? 'element' : 'elements'}
                                        </Tag>
                                    )}
                                    <a
                                        href={
                                            idPrefix === 'violation'
                                                ? `/reports/${report.report_id}?rule=${encodeURIComponent(ruleId)}#violation-${encodeURIComponent(ruleId)}`
                                                : `/reports/${report.report_id}#${idPrefix}-${encodeURIComponent(ruleId)}`
                                        }
                                        className="text-blue-600 hover:underline"
                                        style={{
                                            flex: 1,
                                            overflow: 'hidden',
                                            textOverflow: 'ellipsis',
                                            whiteSpace: 'nowrap',
                                        }}
                                        title={report.url}
                                    >
                                        {report.url}
                                    </a>
                                    {canScan && (
                                        <span style={{ marginLeft: 8 }}>
                                            <RescanPageButton
                                                siteId={report.site_id}
                                                pageUrl={report.url}
                                                size="small"
                                                onScanned={onPageScanned}
                                            />
                                        </span>
                                    )}
                                </li>
                            ))}
                    </ul>
                ),
            },
        ];

        return (
            <Card id={cardId} style={{ marginBottom: '16px' }} title={title} extra={badge}>
                {header}
                {ruleFindings && (
                    <RuleFindingsSummary
                        ruleId={ruleId}
                        group={ruleFindings}
                        canEdit={canEdit}
                        onBulkStatus={onBulkStatus}
                    />
                )}
                {!!accessibilityResult.reports?.length && (
                    <div className="mt-4">
                        <Collapse items={reportItems}></Collapse>
                    </div>
                )}
                {!!accessibilityResult.nodes?.length && (
                    <div className="mt-2">
                        <NodeList
                            ruleId={ruleId}
                            nodes={accessibilityResult.nodes}
                            label={
                                nodeLabel ??
                                // The samples come from the page the website report met first
                                // (reports[0], before the list above is sorted by count).
                                `Example elements from ${accessibilityResult.reports[0]?.url.replace(/^https?:\/\//, '') ?? 'one page'}`
                            }
                            open={false}
                        />
                    </div>
                )}
                {footer}
            </Card>
        );
    }

    return (
        <Card id={cardId} style={{ marginBottom: '16px' }} title={title} extra={badge}>
            {header}
            {!!accessibilityResult.nodes?.length && (
                <div className="mt-2">
                    <NodeList
                        ruleId={ruleId}
                        nodes={accessibilityResult.nodes}
                        label={nodeLabel ?? 'Elements'}
                        // Failing elements are the to-do; elements to check stay folded.
                        open={idPrefix === 'violation'}
                        previewEnabled={previewEnabled}
                        findingsBySelector={findingsBySelector}
                        canEdit={canEdit}
                        onFindingChanged={onFindingChanged}
                    />
                </div>
            )}
            {footer}
        </Card>
    );
}

export default AuditAccessibilityItem;

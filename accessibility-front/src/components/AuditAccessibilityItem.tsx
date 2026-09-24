'use client';
import { STATUS_COLORS, STATUS_LABELS } from '@/lib/findings';
import { ImpactTag } from '@/lib/impact';
import { AxeNode, AxeResult, WebsiteAxeResult } from '@/lib/types/axe';
import { Finding, FindingRuleGroup, FindingStatus } from '@/lib/types/finding';
import { Button, Card, Collapse, Dropdown, Tag, Tooltip } from 'antd';
import { useState } from 'react';
import { useGuides } from '@/hooks/useGuides';
import { guideHref } from '@/lib/guides';
import Link from 'next/link';
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
    onBulkStatus?: (ruleId: string, status: FindingStatus) => Promise<void>;
};

const NODE_PAGE = 10;

function isWebsiteResult(result: WebsiteAxeResult | AxeResult): result is WebsiteAxeResult {
    return (result as WebsiteAxeResult).reports !== undefined;
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
                    children: (
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
    onBulkStatus?: (ruleId: string, status: FindingStatus) => Promise<void>;
}) {
    const [busy, setBusy] = useState(false);
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
                <Dropdown
                    menu={{
                        items: (Object.keys(STATUS_LABELS) as FindingStatus[]).map((status) => ({
                            key: status,
                            label: STATUS_LABELS[status],
                        })),
                        onClick: async ({ key }) => {
                            setBusy(true);
                            await onBulkStatus(ruleId, key as FindingStatus);
                            setBusy(false);
                        },
                    }}
                >
                    <Button size="small" loading={busy}>
                        Mark all on this website as…
                    </Button>
                </Dropdown>
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
}: Props) {
    const guides = useGuides();
    if (!accessibilityResult) return <div>No accessibility result provided.</div>;

    const ruleId = accessibilityResult.id;
    const header = (
        <>
            <div className="mb-2 text-gray-700">{accessibilityResult.description}</div>
            <div className="text-sm text-gray-500">
                <strong>Help:</strong> {accessibilityResult.help}
            </div>
        </>
    );
    const footer = (
        <>
            <div className="mt-2 flex flex-wrap justify-end gap-2">
                {accessibilityResult.tags &&
                    accessibilityResult.tags.map((tag, index) => (
                        <Tag key={index} color="default">
                            {tag}
                        </Tag>
                    ))}
            </div>
            <div className="mt-2 flex justify-end-safe gap-4">
                {guides.has(ruleId) && <Link href={guideHref(ruleId)}>Fix guide</Link>}
                <a href={accessibilityResult.helpUrl} target="_blank" rel="noopener noreferrer">
                    Learn more
                </a>
            </div>
        </>
    );

    if (isWebsiteResult(accessibilityResult)) {
        const reportItems: Parameters<typeof Collapse>[0]['items'] = [
            {
                key: 'pages',
                label: (
                    <Tooltip title="Pages where this issue was found (click to expand)">
                        <span className="font-medium">
                            Affected URLs
                            <Tag color="blue" style={{ marginLeft: 8 }}>
                                {accessibilityResult.reports.length}
                            </Tag>
                        </span>
                    </Tooltip>
                ),
                children: (
                    <ul style={{ paddingLeft: 0, margin: 0 }}>
                        {accessibilityResult.reports.map((report, idx) => (
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
                                    href={`/reports/${report.report_id}?rule=${encodeURIComponent(ruleId)}#violation-${encodeURIComponent(ruleId)}`}
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
                            </li>
                        ))}
                    </ul>
                ),
            },
        ];

        return (
            <Card
                id={`violation-${ruleId}`}
                style={{ marginBottom: '16px' }}
                title={<span className="text-lg font-semibold">{ruleId}</span>}
                extra={<ImpactTag impact={accessibilityResult.impact} />}
            >
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
                            label="Example elements (from the first affected page)"
                            open={false}
                        />
                    </div>
                )}
                {footer}
            </Card>
        );
    }

    return (
        <Card
            id={`violation-${ruleId}`}
            style={{ marginBottom: '16px' }}
            title={<span className="text-lg font-semibold">{ruleId}</span>}
            extra={<ImpactTag impact={accessibilityResult.impact} />}
        >
            {header}
            {!!accessibilityResult.nodes?.length && (
                <div className="mt-2">
                    <NodeList
                        ruleId={ruleId}
                        nodes={accessibilityResult.nodes}
                        label="Elements"
                        open
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

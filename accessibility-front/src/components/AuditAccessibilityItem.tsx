'use client';
import { isSuppressed, REASON_MIN_LENGTH, STATUS_COLORS, STATUS_LABELS } from '@/lib/findings';
import { ImpactTag } from '@/lib/impact';
import { AxeNode, AxeResult, WebsiteAxeResult } from '@/lib/types/axe';
import { Finding, FindingRuleGroup, FindingStatus } from '@/lib/types/finding';
import { Button, Card, Collapse, Input, Modal, Radio, Tag, Tooltip } from 'antd';
import { useState } from 'react';
import { useGuides } from '@/hooks/useGuides';
import { guideHref } from '@/lib/guides';
import RescanPageButton from './RescanPageButton';
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
    onBulkStatus?: (ruleId: string, status: FindingStatus, note?: string) => Promise<void>;
}) {
    const [busy, setBusy] = useState(false);
    const [open, setOpen] = useState(false);
    // Nothing chosen to start with: a stray Enter must not mark a whole rule fixed.
    const [choice, setChoice] = useState<FindingStatus | null>(null);
    const [reason, setReason] = useState('');
    const total = Object.values(group.counts).reduce((sum, n) => sum + n, 0);
    const needsReason = choice !== null && isSuppressed(choice);
    const blocked =
        choice === null
            ? 'Choose a status.'
            : needsReason && !reason.trim()
              ? `Add a reason of at least ${REASON_MIN_LENGTH} characters.`
              : needsReason && reason.trim().length < REASON_MIN_LENGTH
                ? `The reason needs at least ${REASON_MIN_LENGTH} characters.`
                : null;
    const suppressed = group.counts.false_positive + group.counts.accepted;
    const close = () => {
        setOpen(false);
        setReason('');
        setChoice(null);
    };
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
                // Site-wide and easy to get wrong, so one dialog holds the whole decision:
                // the status, the size, and a reason when the status hides elements. A
                // dialog takes focus, closes on Escape and gives focus back to this button.
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
                    <Modal
                        open={open}
                        title={`Status for all ${total} element${total === 1 ? '' : 's'} of this rule`}
                        okText={
                            choice
                                ? `Mark ${total} as ${STATUS_LABELS[choice].toLowerCase()}`
                                : 'Mark them'
                        }
                        okButtonProps={{ disabled: blocked !== null }}
                        onOk={async () => {
                            const status = choice;
                            if (!status) return;
                            const note = isSuppressed(status) ? reason.trim() : undefined;
                            close();
                            setBusy(true);
                            await onBulkStatus(ruleId, status, note);
                            setBusy(false);
                        }}
                        onCancel={close}
                    >
                        <p className="text-sm text-gray-700" style={{ margin: '0 0 12px' }}>
                            On every page of this website.
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
                                    <span className="ml-2 text-sm text-gray-600">
                                        {STATUS_HINTS[status]}
                                    </span>
                                </Radio>
                            ))}
                        </Radio.Group>
                        {needsReason && (
                            <div style={{ marginTop: 16 }}>
                                <p id={`reason-why-${ruleId}`} style={{ margin: '0 0 8px' }}>
                                    They will no longer count in this website&apos;s totals, Fix
                                    first or the dashboard. Reviewers see who marked them and why.
                                </p>
                                <label htmlFor={`reason-${ruleId}`} className="text-sm font-medium">
                                    Reason (required, at least {REASON_MIN_LENGTH} characters)
                                </label>
                                <Input.TextArea
                                    id={`reason-${ruleId}`}
                                    rows={3}
                                    maxLength={2000}
                                    value={reason}
                                    aria-required
                                    aria-describedby={`reason-why-${ruleId}`}
                                    onChange={(e) => setReason(e.target.value)}
                                    style={{ marginTop: 4 }}
                                />
                            </div>
                        )}
                        {/* Why the confirm button is off, said instead of left to guess. */}
                        <output className="mt-3 block text-sm text-gray-700">{blocked}</output>
                    </Modal>
                </>
            )}
        </div>
    );
}

// What each status means, said where the choice is made.
const STATUS_HINTS: Record<FindingStatus, string> = {
    open: 'still to fix',
    fixed: 'changed on the site; the next scan confirms it',
    false_positive: 'the check is wrong about these elements',
    accepted: 'known, and will not be fixed',
};

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

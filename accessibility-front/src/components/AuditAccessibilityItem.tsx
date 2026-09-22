'use client';
import { ImpactTag } from '@/lib/impact';
import { AxeNode, AxeResult, WebsiteAxeResult } from '@/lib/types/axe';
import { Button, Card, Collapse, Tag, Tooltip } from 'antd';
import { useState } from 'react';
import ViolationNode from './ViolationNode';

type Props = {
    accessibilityResult: WebsiteAxeResult | AxeResult;
    // Offer "Show in preview" on each element (the report page, where the preview iframe is).
    previewEnabled?: boolean;
};

const NODE_PAGE = 10;

function isWebsiteResult(result: WebsiteAxeResult | AxeResult): result is WebsiteAxeResult {
    return (result as WebsiteAxeResult).reports !== undefined;
}

// A rule's failing elements, ten at a time so a rule with hundreds stays cheap to open.
function NodeList({
    nodes,
    label,
    open,
    previewEnabled,
}: {
    nodes: AxeNode[];
    label: string;
    open: boolean;
    previewEnabled?: boolean;
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

function AuditAccessibilityItem({ accessibilityResult, previewEnabled = false }: Props) {
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
            <div className="mt-2 flex justify-end-safe">
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
                {!!accessibilityResult.reports?.length && (
                    <div className="mt-4">
                        <Collapse items={reportItems}></Collapse>
                    </div>
                )}
                {!!accessibilityResult.nodes?.length && (
                    <div className="mt-2">
                        <NodeList
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
                        nodes={accessibilityResult.nodes}
                        label="Elements"
                        open
                        previewEnabled={previewEnabled}
                    />
                </div>
            )}
            {footer}
        </Card>
    );
}

export default AuditAccessibilityItem;

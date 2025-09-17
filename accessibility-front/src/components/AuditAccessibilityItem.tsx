import { AxeResult, WebsiteAxeResult } from '@/lib/types/axe';
import { Card, Tag } from 'antd';

type Props = {
    accessibilityResult: WebsiteAxeResult | AxeResult;
};

function AuditAccessibilityItem({ accessibilityResult }: Props) {
    if (!accessibilityResult) return <div>No accessibility result provided.</div>;

    const isWebsiteResult = (result: WebsiteAxeResult | AxeResult): result is WebsiteAxeResult => {
        return (result as WebsiteAxeResult).reports !== undefined;
    };

    if (isWebsiteResult(accessibilityResult)) {
        return (
            <Card
                style={{ marginBottom: '16px' }}
                title={<span className="text-lg font-semibold">{accessibilityResult.id}</span>}
                extra={
                    <Tag color={accessibilityResult.impact === 'critical' ? 'red' : 'blue'}>
                        {accessibilityResult.impact}
                    </Tag>
                }
            >
                <div className="mb-2 text-gray-700">{accessibilityResult.description}</div>
                <div className="text-sm text-gray-500">
                    <strong>Help:</strong> {accessibilityResult.help}
                </div>

                {!!accessibilityResult.reports?.length && (
                    <div className="mt-4">
                        <strong className="block mb-2 text-gray-800">Reported on:</strong>
                        <ul className="space-y-2">
                            {accessibilityResult.reports.map((report) => (
                                <li key={report.report_id}>
                                    <Card
                                        size="small"
                                        type="inner"
                                        className="hover:shadow-md transition"
                                    >
                                        {' '}
                                        <a
                                            href={`/reports/${report.report_id}`}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            style={{
                                                color: '#1677ff',
                                                fontWeight: 500,
                                                wordBreak: 'break-all',
                                            }}
                                            title={report.url}
                                        >
                                            {report.url}
                                        </a>
                                    </Card>
                                </li>
                            ))}
                        </ul>
                    </div>
                )}
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
            </Card>
        );
    }

    return (
        <Card
            style={{ marginBottom: '16px' }}
            title={<span className="text-lg font-semibold">{accessibilityResult.id}</span>}
            extra={
                <Tag color={accessibilityResult.impact === 'critical' ? 'red' : 'blue'}>
                    {accessibilityResult.impact}
                </Tag>
            }
        >
            <div className="mb-2 text-gray-700">{accessibilityResult.description}</div>
            <div className="text-sm text-gray-500">
                <strong>Help:</strong> {accessibilityResult.help}
            </div>

            {accessibilityResult.nodes && (
                <div className="mt-2">
                    <strong>Nodes:</strong>
                    <ul className="list-inside list-disc">
                        {accessibilityResult.nodes.map((node, idx) => (
                            <li key={idx} className="text-xs text-gray-600">
                                {node.target.join(', ')}
                            </li>
                        ))}
                    </ul>
                </div>
            )}
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
        </Card>
    );
}

export default AuditAccessibilityItem;

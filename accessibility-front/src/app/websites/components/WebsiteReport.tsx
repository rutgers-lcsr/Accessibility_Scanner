'use client';
import AuditAccessibilityItem from '@/components/AuditAccessibilityItem';
import { WebsiteAxeReport } from '@/lib/types/axe';
import { Button, Card, Flex, Select } from 'antd';
import { useState } from 'react';

type Props = {
    report: WebsiteAxeReport;
};

function WebsiteReport({ report }: Props) {
    const [desc, setDesc] = useState(true);
    const [sortKey, setSortKey] = useState<'impact' | 'reports'>('reports');

    if (!report) return <div>No report data available.</div>;

    if (report.violations.length === 0)
        return (
            <div className="mt-2">
                <Card title="Accessibility Violations">
                    <div className="text-center text-green-600">
                        No accessibility violations found.
                    </div>
                </Card>
            </div>
        );

    const sortedViolations = [...report.violations].sort((a, b) => {
        if (sortKey === 'impact') {
            const impactOrder = { critical: 4, serious: 3, moderate: 2, minor: 1 };
            const impactA = a.impact ? impactOrder[a.impact] : 0;
            const impactB = b.impact ? impactOrder[b.impact] : 0;
            return desc ? impactB - impactA : impactA - impactB;
        } else if (sortKey === 'reports') {
            const reportsA = a.reports ? a.reports.length : 0;
            const reportsB = b.reports ? b.reports.length : 0;
            return desc ? reportsB - reportsA : reportsA - reportsB;
        }
        return 0;
    });

    return (
        <div className="mt-2">
            <Card
                title={<span className="font-semibold text-lg">Accessibility Violations</span>}
                extra={
                    <Flex gap={12} align="center">
                        <span className="text-gray-600">Sort by</span>
                        <Select
                            value={sortKey}
                            onChange={(e) => setSortKey(e as 'impact' | 'reports')}
                            size="small"
                            style={{ minWidth: 140 }}
                        >
                            <Select.Option value="impact">Impact</Select.Option>
                            <Select.Option value="reports"># of Reports</Select.Option>
                        </Select>
                        <Button
                            onClick={() => setDesc(!desc)}
                            size="small"
                            type="default"
                            icon={
                                desc ? (
                                    <span aria-label="Descending" role="img">
                                        ↓
                                    </span>
                                ) : (
                                    <span aria-label="Ascending" role="img">
                                        ↑
                                    </span>
                                )
                            }
                        >
                            {desc ? 'Desc' : 'Asc'}
                        </Button>
                    </Flex>
                }
                styles={{ body: { paddingTop: 16, paddingBottom: 16 } }}
            >
                <div className="pt-4 pb-4">
                    {sortedViolations.map((violation, index) => (
                        <AuditAccessibilityItem key={index} accessibilityResult={violation} />
                    ))}
                </div>
            </Card>
        </div>
    );
}

export default WebsiteReport;

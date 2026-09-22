'use client';
import ViolationsList from '@/components/ViolationsList';
import { WebsiteAxeReport } from '@/lib/types/axe';
import { Card } from 'antd';

type Props = {
    report: WebsiteAxeReport;
};

function WebsiteReport({ report }: Props) {
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

    return (
        <div className="mt-2">
            <Card
                title={<span className="font-semibold text-lg">Accessibility Violations</span>}
                styles={{ body: { paddingTop: 16, paddingBottom: 16 } }}
            >
                <ViolationsList violations={report.violations} pages={pages} />
            </Card>
        </div>
    );
}

export default WebsiteReport;

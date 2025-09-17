import AuditAccessibilityItem from '@/components/AuditAccessibilityItem';
import { WebsiteAxeReport } from '@/lib/types/axe';
import { Card } from 'antd';

type Props = {
    report: WebsiteAxeReport;
};

function WebsiteReport({ report }: Props) {
    return (
        <div className="mt-2">
            <Card title="Accessibility Violations">
                <div className="mt-4">
                    {report.violations.map((violation, index) => (
                        <AuditAccessibilityItem key={index} accessibilityResult={violation} />
                    ))}
                </div>
            </Card>
        </div>
    );
}

export default WebsiteReport;

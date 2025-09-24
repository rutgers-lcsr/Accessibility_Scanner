'use client';
import { Report, ReportMinimized } from '@/lib/types/axe';
import { scanResponse } from '@/lib/types/scan';
import { useAlerts } from '@/providers/Alerts';
import { useUser } from '@/providers/User';
import { Button, Descriptions, Space } from 'antd';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

type Props = {
    report: Report;
};

function AdminReportItems({ report }: Props) {
    const router = useRouter();
    const { addAlert } = useAlerts();

    const [loadingScan, setLoadingScan] = useState(false);

    const { handlerUserApiRequest } = useUser();

    const handleScan = async () => {
        setLoadingScan(true);
        try {
            const scanResponse = await handlerUserApiRequest<scanResponse>(
                `/api/scans/scan/?site=${report.site_id}`,
                {
                    method: 'POST',
                }
            );
            addAlert('Scan initiated successfully', 'info');

            async function pollReport() {
                await new Promise((resolve) => setTimeout(resolve, 2000)); // wait for 2 seconds
                try {
                    const newReport = await handlerUserApiRequest<ReportMinimized>(
                        scanResponse.polling_endpoint,
                        {
                            method: 'GET',
                        }
                    );
                    if (newReport && newReport.id) {
                        setLoadingScan(false);
                        router.push(`/reports/${newReport.id}`);
                        addAlert('Scan completed successfully', 'success');
                    } else {
                        return await pollReport(); // recursively poll until we get the report
                    }
                } catch {
                    return await pollReport(); // in case of error, keep polling
                }
            }
            await pollReport();
        } catch (error) {
            console.error('Failed to initiate scan:', error);
            addAlert('Failed to initiate scan', 'error');
            setLoadingScan(false);
        }
    };

    return (
        <div
            className="mb-4 rounded-md bg-gray-50 p-4 shadow"
            aria-label="Report Overview Information"
        >
            <Space className="w-full" size={'large'} direction="vertical">
                <Descriptions
                    size="small"
                    column={3}
                    layout="horizontal"
                    title="Site Info"
                    bordered
                >
                    <Descriptions.Item label="Site ID">{report.site_id}</Descriptions.Item>
                    <Descriptions.Item label="URL">{report.url}</Descriptions.Item>
                    <Descriptions.Item label="Actions">
                        <Button
                            type="primary"
                            loading={loadingScan}
                            onClick={handleScan}
                            disabled={loadingScan}
                        >
                            {loadingScan ? 'Scanning...' : 'Re-scan Site'}
                        </Button>
                    </Descriptions.Item>
                    <Descriptions.Item label="Report ID">{report.id}</Descriptions.Item>
                    <Descriptions.Item label="Report Date">
                        {report?.timestamp ? new Date(report.timestamp).toLocaleString() : 'N/A'}
                    </Descriptions.Item>
                    <Descriptions.Item label="Total Violations">
                        {report.report_counts.violations.total}
                    </Descriptions.Item>
                    <Descriptions.Item label="Total Passes">
                        {report.report_counts.passes.total}
                    </Descriptions.Item>
                    <Descriptions.Item label="Total Incomplete">
                        {report.report_counts.incomplete.total}
                    </Descriptions.Item>
                </Descriptions>
            </Space>
        </div>
    );
}

export default AdminReportItems;

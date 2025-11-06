'use client';
import { Report, ReportMinimized } from '@/lib/types/axe';
import { scanResponse } from '@/lib/types/scan';
import { useAlerts } from '@/providers/Alerts';
import { useUser } from '@/providers/User';
import ScanProgressModal from '@/components/ScanProgressModal';
import { Button, Descriptions, Space, Tooltip } from 'antd';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

type Props = {
    report: Report;
};

function AdminReportItems({ report }: Props) {
    const router = useRouter();
    const { addAlert } = useAlerts();
    const { handlerUserApiRequest } = useUser();

    const [loadingScan, setLoadingScan] = useState(false);
    const [taskId, setTaskId] = useState<string | null>(null);
    const [taskStatusEndpoint, setTaskStatusEndpoint] = useState<string | null>(null);
    const [reportPollingEndpoint, setReportPollingEndpoint] = useState<string | null>(null);
    const [showProgress, setShowProgress] = useState(false);

    const pollReport = async (pollingEndpoint: string) => {
        await new Promise((resolve) => setTimeout(resolve, 2000));
        try {
            const newReport = await handlerUserApiRequest<ReportMinimized>(pollingEndpoint, {
                method: 'GET',
            });
            if (newReport && newReport.id) {
                setLoadingScan(false);
                router.push(`/reports/${newReport.id}`);
                addAlert('Scan completed successfully', 'success');
            } else {
                return await pollReport(pollingEndpoint);
            }
        } catch {
            return await pollReport(pollingEndpoint);
        }
    };

    const handleScan = async () => {
        setLoadingScan(true);
        try {
            const scanResponse = await handlerUserApiRequest<scanResponse>(
                `/api/scans/scan/?site=${report.site_id}`,
                { method: 'POST' }
            );

            if (
                scanResponse.task_id &&
                scanResponse.status_endpoint &&
                scanResponse.polling_endpoint
            ) {
                setTaskId(scanResponse.task_id);
                setTaskStatusEndpoint(scanResponse.status_endpoint);
                setReportPollingEndpoint(scanResponse.polling_endpoint);
                setShowProgress(true);
                addAlert('Scan initiated successfully', 'info');
            } else {
                // Fallback to old polling approach if task tracking not available
                addAlert('Scan initiated successfully', 'info');
                await pollReport(scanResponse.polling_endpoint);
            }
        } catch (error) {
            console.error('Failed to initiate scan:', error);
            addAlert('Failed to initiate scan', 'error');
            setLoadingScan(false);
        }
    };

    const handleScanComplete = async () => {
        setShowProgress(false);
        setLoadingScan(true);

        if (reportPollingEndpoint) {
            await pollReport(reportPollingEndpoint);
        } else {
            setLoadingScan(false);
            addAlert('Scan completed successfully', 'success');
        }
    };

    const handleScanError = (error: string) => {
        setShowProgress(false);
        setLoadingScan(false);
        addAlert(`Scan failed: ${error}`, 'error');
    };

    const handleCloseProgress = () => {
        setShowProgress(false);
        setLoadingScan(false);
    };

    return (
        <div
            className="mb-4 rounded-md bg-gray-50 p-4 shadow"
            aria-label="Report Overview Information"
        >
            <Space className="w-full" size={'large'} direction="vertical">
                <Descriptions size="small" column={3} layout="horizontal" title="Url Info" bordered>
                    <Descriptions.Item label="Actions">
                        <Button
                            type="primary"
                            loading={loadingScan}
                            onClick={handleScan}
                            disabled={loadingScan}
                        >
                            {loadingScan ? 'Scanning...' : 'Scan Url'}
                        </Button>
                    </Descriptions.Item>
                    <Descriptions.Item label="Tags">
                        <Tooltip
                            title={'Rule tags which are applied to this report'}
                            placement="top"
                        >
                            <span>{report.tags.join(', ')}</span>
                        </Tooltip>
                    </Descriptions.Item>
                </Descriptions>
            </Space>
            {taskId && taskStatusEndpoint && (
                <ScanProgressModal
                    taskId={taskId}
                    statusEndpoint={taskStatusEndpoint}
                    onComplete={handleScanComplete}
                    onError={handleScanError}
                    visible={showProgress}
                    onClose={handleCloseProgress}
                />
            )}
        </div>
    );
}

export default AdminReportItems;

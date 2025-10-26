'use client';
import { useState } from 'react';
import { useUser } from '@/providers/User';
import { useAlerts } from '@/providers/Alerts';
import { scanResponse } from '@/lib/types/scan';
import { Website } from '@/lib/types/website';

type UseScanOptions = {
    websiteId?: number;
    siteId?: number;
    onComplete?: () => void;
};

export function useScan({ websiteId, siteId, onComplete }: UseScanOptions) {
    const { handlerUserApiRequest } = useUser();
    const { addAlert } = useAlerts();
    const [loading, setLoading] = useState(false);
    const [taskId, setTaskId] = useState<string | null>(null);
    const [statusEndpoint, setStatusEndpoint] = useState<string | null>(null);
    const [showProgress, setShowProgress] = useState(false);

    const startScan = async () => {
        setLoading(true);
        try {
            const queryParam = websiteId ? `website=${websiteId}` : `site=${siteId}`;
            const response = await handlerUserApiRequest<scanResponse>(
                `/api/scans/scan?${queryParam}`,
                {
                    method: 'POST',
                }
            );

            // Use new task status modal if available
            if (response.task_id && response.status_endpoint) {
                setTaskId(response.task_id);
                setStatusEndpoint(response.status_endpoint);
                setShowProgress(true);
                addAlert(response.info ? response.info : 'Scan started!', 'info');
            } else if (response.polling_endpoint) {
                addAlert('Scan started! Please stay on this page.', 'info');
                // Fallback to old polling method
                async function pollReport() {
                    await new Promise((resolve) => setTimeout(resolve, 2000));
                    try {
                        const newReport = await handlerUserApiRequest<Website>(
                            response.polling_endpoint,
                            {
                                method: 'GET',
                            }
                        );
                        if (newReport && newReport.id) {
                            setLoading(false);
                            if (onComplete) onComplete();
                            addAlert('Scan completed successfully', 'success');
                        } else {
                            return await pollReport();
                        }
                    } catch {
                        return await pollReport();
                    }
                }
                await pollReport();
            }
        } catch (error) {
            if (error instanceof Error) {
                addAlert('Failed to initiate scan: ' + error.message, 'error');
            } else {
                addAlert('Failed to initiate scan', 'error');
            }
            console.error('Failed to initiate scan:', error);
            addAlert('Failed to initiate scan', 'error');
            setLoading(false);
        }
    };

    const handleScanComplete = () => {
        setLoading(false);
        setShowProgress(false);
        addAlert('Scan completed successfully!', 'success');
        if (onComplete) onComplete();
    };

    const handleScanError = (error: string) => {
        setLoading(false);
        addAlert(`Scan failed: ${error}`, 'error');
    };

    const handleCloseProgress = () => {
        setShowProgress(false);
    };

    return {
        loading,
        taskId,
        statusEndpoint,
        showProgress,
        startScan,
        handleScanComplete,
        handleScanError,
        handleCloseProgress,
    };
}

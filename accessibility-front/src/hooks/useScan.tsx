'use client';
import { useState } from 'react';
import { useUser } from '@/providers/User';
import { useAlerts } from '@/providers/Alerts';
import { APIError } from '@/lib/api';
import { scanResponse, TaskStatus } from '@/lib/types/scan';
import { Website } from '@/lib/types/website';

type UseScanOptions = {
    websiteId?: number;
    siteId?: number;
    // Audit one page ad hoc (POST /api/scans/quick); startScan then takes the URL.
    quick?: boolean;
    onComplete?: (status?: TaskStatus) => void;
    // Leave the progress modal open on completion (a page rescan shows what changed there).
    closeOnComplete?: boolean;
};

export function useScan({
    websiteId,
    siteId,
    quick = false,
    onComplete,
    closeOnComplete = true,
}: UseScanOptions) {
    const { handlerUserApiRequest } = useUser();
    const { addAlert } = useAlerts();
    const [loading, setLoading] = useState(false);
    const [taskId, setTaskId] = useState<string | null>(null);
    const [statusEndpoint, setStatusEndpoint] = useState<string | null>(null);
    const [resultEndpoint, setResultEndpoint] = useState<string | null>(null);
    const [showProgress, setShowProgress] = useState(false);

    const startScan = async (url?: string) => {
        setLoading(true);
        try {
            const response = quick
                ? await handlerUserApiRequest<scanResponse>('/api/scans/quick', {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ url }),
                  })
                : await handlerUserApiRequest<scanResponse>(
                      `/api/scans/scan?${websiteId ? `website=${websiteId}` : `site=${siteId}`}`,
                      { method: 'POST' }
                  );

            // Use new task status modal if available
            if (response.task_id && response.status_endpoint) {
                setTaskId(response.task_id);
                setStatusEndpoint(response.status_endpoint);
                setResultEndpoint(response.result_endpoint ?? null);
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
            const apiError = error as APIError;
            if (apiError?.details?.code === 'not_allowed_domain') {
                addAlert(
                    `Quick scans are limited to allowed domains; ${apiError.details.domain} is not under one`,
                    'error'
                );
            } else if (apiError?.response?.status === 409) {
                addAlert(
                    quick
                        ? 'You already have a quick scan running; wait for it to finish'
                        : 'This page is already being scanned; wait for it to finish',
                    'warning'
                );
            } else if (apiError?.response?.status === 429) {
                addAlert('You can start five scans a minute; try again in a moment', 'warning');
            } else if (error instanceof Error) {
                addAlert('Failed to initiate scan: ' + error.message, 'error');
            } else {
                addAlert('Failed to initiate scan', 'error');
            }
            setLoading(false);
        }
    };

    const handleScanComplete = (status?: TaskStatus) => {
        setLoading(false);
        if (closeOnComplete) {
            setShowProgress(false);
            addAlert('Scan completed successfully!', 'success');
        }
        if (onComplete) onComplete(status);
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
        resultEndpoint,
        showProgress,
        startScan,
        handleScanComplete,
        handleScanError,
        handleCloseProgress,
    };
}

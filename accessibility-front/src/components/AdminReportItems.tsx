'use client';
import { Report, ReportMinimized } from '@/lib/types/axe';
import { scanResponse } from '@/lib/types/scan';
import { useAlerts } from '@/providers/Alerts';
import { useUser } from '@/providers/User';
import { Button, Space } from 'antd';
import { useRouter } from 'next/navigation';
import React, { useState } from 'react';

type Props = {
    report: Report;
};

function AdminReportItems({ report }: Props) {
    const router = useRouter();
    const { addAlert } = useAlerts();

    const [loadingScan, setLoadingScan] = useState(false);

    const { is_admin, handlerUserApiRequest } = useUser();
    if (!is_admin) return null;

    const handleScan = async () => {
        setLoadingScan(true);
        try {
            const scanResponse = await handlerUserApiRequest<scanResponse>(
                `/api/scans/scan?site=${report.site_id}`,
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
                        router.push(`/reports?id=${newReport.id}`);
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
        <div className="mb-4">
            <Space>
                <Button onClick={handleScan} loading={loadingScan}>
                    Scan Now
                </Button>
            </Space>
        </div>
    );
}

export default AdminReportItems;

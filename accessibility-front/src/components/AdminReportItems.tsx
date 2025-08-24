import { Report, ReportMinimized } from '@/lib/types/axe';
import { scanResponse, scanResponseSite } from '@/lib/types/scan';
import { useUser } from '@/providers/User';
import { Button, Space } from 'antd';
import { useRouter } from 'next/navigation';
import React, { useState } from 'react'
import useSWR from 'swr';

type Props = {
    report: Report;
}

function AdminReportItems({ report }: Props) {
    const router = useRouter();
    const [loadingScan, setLoadingScan] = useState(false);
    const { handlerUserApiRequest } = useUser();



    const handleScan = async () => {
        setLoadingScan(true);
        console.log(report)
        const scanResponse = await handlerUserApiRequest<scanResponse>(`/api/scans/scan?site=${report.site_id}`, {
            method: 'POST'
        });


        async function pollReport() {
            await new Promise(resolve => setTimeout(resolve, 2000)); // wait for 2 seconds
            try {
                const newReport = await handlerUserApiRequest<ReportMinimized>(scanResponse.polling_endpoint, {
                    'method': 'GET'
                });
                if (newReport && newReport.id) {
                    setLoadingScan(false);
                    router.push(`/reports?id=${newReport.id}`);
                } else {
                    return await pollReport(); // recursively poll until we get the report
                }
            }
            catch {
                return await pollReport(); // in case of error, keep polling
            }
        }
        await pollReport();
    }

    return (
        <div className='mb-4'>
            <Space>

                <Button onClick={handleScan} loading={loadingScan}>Scan Now</Button>

            </Space>
        </div>
    )
}

export default AdminReportItems
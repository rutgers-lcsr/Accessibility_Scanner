import { Report, ReportMinimized } from '@/lib/types/axe';
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

    // const { data: site } = useSWR<Report>(`/api/reports/${site.id}`, fetcherApi);

    return (
        <div className='mb-4'>
            <Space>

                <Button onClick={async () => {
                    setLoadingScan(true);
                    console.log(report)
                    const newReport = await handlerUserApiRequest<ReportMinimized>(`/api/scans/scan?site=${report.site_id}`, {
                        method: 'POST'
                    });
                    setLoadingScan(false);
                    router.push(`/reports?id=${newReport.id}`);
                }} loading={loadingScan}>Scan Now</Button>

            </Space>
        </div>
    )
}

export default AdminReportItems
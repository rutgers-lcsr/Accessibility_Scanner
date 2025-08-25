import { useUser } from '@/providers/User';
import { Website } from '@/lib/types/website';
import { scanResponse } from '@/lib/types/scan';
import { Button, InputNumber, Space, Tooltip } from 'antd';
import React, { useState } from 'react'
import { KeyedMutator } from 'swr';
import { useAlerts } from '@/providers/Alerts';

type Props = {
    website: Website;
    mutate: KeyedMutator<Website>;

}

function AdminWebsiteItems({ website, mutate }: Props) {
    const { addAlert } = useAlerts();
    const [loadingScan, setLoadingScan] = useState(false);
    const [loadingActivate, setLoadingActivate] = useState(false);
    const [loadingRateLimit, setLoadingRateLimit] = useState(false);

    const { handlerUserApiRequest } = useUser();




    const handleScan = async () => {
        setLoadingScan(true);
        try {
            const scanResponse = await handlerUserApiRequest<scanResponse>(`/api/scans/scan?website=${website.id}`, {
                method: 'POST'
            });
            addAlert("Scan initiated successfully", "info");

            async function pollReport() {
                await new Promise(resolve => setTimeout(resolve, 2000)); // wait for 2 seconds
                try {
                    const newReport = await handlerUserApiRequest<Website>(scanResponse.polling_endpoint, {
                        'method': 'GET'
                    });
                    if (newReport && newReport.id) {
                        setLoadingScan(false);
                        mutate();
                        addAlert("Scan completed successfully", "success");
                    } else {
                        return await pollReport(); // recursively poll until we get the report
                    }
                }
                catch {
                    return await pollReport(); // in case of error, keep polling
                }
            }
            await pollReport();
        } catch (error) {
            console.error("Failed to initiate scan:", error);
            addAlert("Failed to initiate scan", "error");
            setLoadingScan(false);
        }

    }
    const handleActivate = async () => {
        setLoadingActivate(true);
        try {
            const updatedWebsite = await handlerUserApiRequest<Website>(`/api/websites/${website.id}`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ active: !website.active })
            });
            mutate(updatedWebsite);
            addAlert(`Website ${website.active ? 'deactivated' : 'activated'} successfully`, "success");
        } catch {

            addAlert("Failed to update website", "error");
        }
        setLoadingActivate(false);
    };
    const handleRateLimitChange = async (value: string | null) => {
        if (value !== null) {
            setLoadingRateLimit(true);
            try {
                const updatedWebsite = await handlerUserApiRequest<Website>(`/api/websites/${website.id}`, {
                    method: 'PATCH',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ rate_limit: value })
                });
                mutate(updatedWebsite);
                addAlert("Rate limit updated successfully", "success");
            } catch {
                addAlert("Failed to update rate limit", "error");
            }

            setLoadingRateLimit(false);
        }
    };

    return (
        <div className='mb-4'>
            <Space>

                <Button onClick={handleScan} loading={loadingScan}>Scan Now</Button>

                <Tooltip title="Automatic Website Scanning">
                    <Button loading={loadingActivate} type={website.active ? 'primary' : 'default'} onClick={handleActivate}>
                        {website.active ? 'Deactivate' : 'Activate'}
                    </Button>
                </Tooltip>


                <InputNumber disabled={!website.active || loadingRateLimit} addonAfter='Rate limit in Days' aria-label='Rate Limit in Days' min={1} value={website.rate_limit} onPressEnter={async (e) => {
                    handleRateLimitChange((e.target as HTMLInputElement).value);
                }} />

            </Space>


        </div>
    )
}

export default AdminWebsiteItems
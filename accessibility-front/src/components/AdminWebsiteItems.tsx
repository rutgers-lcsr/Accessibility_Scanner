import { useUser } from '@/providers/User';
import { Website } from '@/lib/types/website';
import { Button, InputNumber, Space, Tooltip } from 'antd';
import React, { useState } from 'react'
import { KeyedMutator } from 'swr';

type Props = {
    website: Website;
    mutate: KeyedMutator<Website>;

}

function AdminWebsiteItems({ website, mutate }: Props) {
    const [loadingScan, setLoadingScan] = useState(false);
    const [loadingActivate, setLoadingActivate] = useState(false);
    const [loadingRateLimit, setLoadingRateLimit] = useState(false);

    const { handlerUserApiRequest } = useUser();

    return (
        <div className='mb-4'>
            <Space>

                <Button onClick={async () => {
                    setLoadingScan(true);
                    await handlerUserApiRequest(`/api/scans/scan?website=${website.id}`, {
                        method: 'POST'
                    });
                    setLoadingScan(false);
                    mutate();
                }} loading={loadingScan}>Scan Now</Button>

                <Tooltip title="Automatic Website Scanning">
                    <Button loading={loadingActivate} type={website.active ? 'primary' : 'default'} onClick={async () => {
                        setLoadingActivate(true);
                        const updatedWebsite = await handlerUserApiRequest<Website>(`/api/websites/${website.id}`, {
                            method: 'PATCH',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({ active: !website.active })
                        });
                        mutate(updatedWebsite);
                        setLoadingActivate(false);
                    }}>
                        {website.active ? 'Deactivate' : 'Activate'}
                    </Button>
                </Tooltip>


                <InputNumber disabled={!website.active || loadingRateLimit} addonAfter='Rate limit in Days' aria-label='Rate Limit in Days' min={1} value={website.rate_limit} onPressEnter={async (value) => {
                    setLoadingRateLimit(true);
                    console.log(value);
                    const updatedWebsite = await handlerUserApiRequest<Website>(`/api/websites/${website.id}`, {
                        method: 'PATCH',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ rate_limit: value.target.value })
                    });
                    mutate(updatedWebsite);
                    setLoadingRateLimit(false);
                }} />

            </Space>


        </div>
    )
}

export default AdminWebsiteItems
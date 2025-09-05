'use client';
import { scanResponse } from '@/lib/types/scan';
import { Website } from '@/lib/types/website';
import { useUser } from '@/providers/User';

import { useAlerts } from '@/providers/Alerts';
import { Button, Input, InputNumber, Modal, Space, Tooltip } from 'antd';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

type Props = {
    website: Website;
    mutate: (website?: Website) => Promise<void>;
};

function AdminWebsiteItems({ website, mutate }: Props) {
    const router = useRouter();
    const { addAlert } = useAlerts();
    const [loadingScan, setLoadingScan] = useState(false);
    const [loadingActivate, setLoadingActivate] = useState(false);
    const [loadingRateLimit, setLoadingRateLimit] = useState(false);
    const [loadingEmail, setLoadingEmail] = useState(false);
    const [loadingDelete, setLoadingDelete] = useState(false);
    const [loadingShouldEmail, setLoadingShouldEmail] = useState(false);
    const [loadingPublic, setLoadingPublic] = useState(false);
    const [showDeleteModal, setShowDeleteModal] = useState(false);
    const { handlerUserApiRequest } = useUser();

    const handleScan = async () => {
        setLoadingScan(true);
        try {
            const scanResponse = await handlerUserApiRequest<scanResponse>(
                `/api/scans/scan?website=${website.id}`,
                {
                    method: 'POST',
                }
            );
            addAlert('Scan initiated successfully, Please stay on this page.', 'info');

            async function pollReport() {
                await new Promise((resolve) => setTimeout(resolve, 2000)); // wait for 2 seconds
                try {
                    const newReport = await handlerUserApiRequest<Website>(
                        scanResponse.polling_endpoint,
                        {
                            method: 'GET',
                        }
                    );
                    if (newReport && newReport.id) {
                        setLoadingScan(false);
                        mutate();
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
    const handleActivate = async () => {
        setLoadingActivate(true);
        try {
            const updatedWebsite = await handlerUserApiRequest<Website>(
                `/api/websites/${website.id}`,
                {
                    method: 'PATCH',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ active: !website.active }),
                }
            );
            mutate(updatedWebsite);
            addAlert(
                `Website ${website.active ? 'deactivated' : 'activated'} successfully`,
                'success'
            );
        } catch {
            addAlert('Failed to update website', 'error');
        }
        setLoadingActivate(false);
    };
    const handleRateLimitChange = async (value: string | null) => {
        if (value !== null) {
            setLoadingRateLimit(true);
            try {
                const updatedWebsite = await handlerUserApiRequest<Website>(
                    `/api/websites/${website.id}`,
                    {
                        method: 'PATCH',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ rate_limit: value }),
                    }
                );
                mutate(updatedWebsite);
                addAlert('Rate limit updated successfully', 'success');
            } catch {
                addAlert('Failed to update rate limit', 'error');
            }

            setLoadingRateLimit(false);
        }
    };
    const handleEmailChange = async (value: string | null) => {
        const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

        if (value !== null) {
            setLoadingEmail(true);
            try {
                // check if value is real email

                if (!regex.test(value)) {
                    addAlert('Please enter a valid email address', 'error');
                    setLoadingEmail(false);
                    return;
                }

                const updatedWebsite = await handlerUserApiRequest<Website>(
                    `/api/websites/${website.id}`,
                    {
                        method: 'PATCH',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ email: value }),
                    }
                );
                mutate(updatedWebsite);
                addAlert('Email updated successfully', 'success');
            } catch {
                addAlert('Failed to update email', 'error');
            }

            setLoadingEmail(false);
        }
    };
    const handleShouldEmailChange = async (value: boolean) => {
        setLoadingShouldEmail(true);
        try {
            const updatedWebsite = await handlerUserApiRequest<Website>(
                `/api/websites/${website.id}`,
                {
                    method: 'PATCH',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ should_email: value }),
                }
            );
            mutate(updatedWebsite);
            addAlert('Email notification preference updated successfully', 'success');
        } catch {
            addAlert('Failed to update email notification preference', 'error');
        }
        setLoadingShouldEmail(false);
    };
    const handleChangePublic = async (value: boolean) => {
        setLoadingPublic(true);
        try {
            const updatedWebsite = await handlerUserApiRequest<Website>(
                `/api/websites/${website.id}`,
                {
                    method: 'PATCH',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ public: value }),
                }
            );
            mutate(updatedWebsite);
            addAlert('Website visibility updated successfully', 'success');
        } catch {
            addAlert('Failed to update website visibility', 'error');
        }
        setLoadingPublic(false);
    };

    const handleDelete = async () => {
        setLoadingDelete(true);
        try {
            await handlerUserApiRequest(`/api/websites/${website.id}`, {
                method: 'DELETE',
            });
            mutate();
            addAlert('Website deleted successfully', 'success');
        } catch {
            addAlert('Failed to delete website', 'error');
        }
        router.back();
        setLoadingDelete(false);
    };

    return (
        <div className="mb-4 flex w-full flex-wrap rounded-md bg-gray-50 p-4 shadow">
            <Space className="w-full" size={'large'} wrap>
                <Button onClick={handleScan} loading={loadingScan}>
                    Scan Now
                </Button>

                <Tooltip title="Automatic Website Scanning">
                    <Button
                        loading={loadingActivate}
                        type={website.active ? 'primary' : 'default'}
                        onClick={handleActivate}
                    >
                        {website.active ? 'Deactivate' : 'Activate'}
                    </Button>
                </Tooltip>

                <InputNumber
                    disabled={!website.active || loadingRateLimit}
                    addonBefore="Rate limit in Days"
                    aria-label="Rate Limit in Days"
                    min={1}
                    value={website.rate_limit}
                    onPressEnter={async (e) => {
                        handleRateLimitChange((e.target as HTMLInputElement).value);
                    }}
                />
                <div className="flex items-center gap-2">
                    <label htmlFor="email">Email</label>
                    <Input
                        id="email"
                        aria-label="Email"
                        placeholder="Email"
                        type="text"
                        defaultValue={website.email}
                        disabled={loadingEmail}
                        onPressEnter={async (e) => {
                            handleEmailChange((e.target as HTMLInputElement).value);
                        }}
                    />
                    <Button
                        type={website.should_email ? 'default' : 'primary'}
                        loading={loadingShouldEmail}
                        onClick={() => handleShouldEmailChange(!website.should_email)}
                    >
                        {website.should_email ? 'Disable Email Notify' : 'Enable Email Notify'}
                    </Button>
                </div>

                <div className="">
                    <Button
                        type={website.public ? 'default' : 'primary'}
                        loading={loadingPublic}
                        onClick={() => handleChangePublic(!website.public)}
                    >
                        {website.public ? 'Disable Public Access' : 'Enable Public Access'}
                    </Button>
                </div>
                <div className="flex justify-end">
                    <Button danger onClick={() => setShowDeleteModal(true)} loading={loadingDelete}>
                        Delete
                    </Button>
                    <Modal
                        title="Confirm Deletion"
                        open={showDeleteModal}
                        onCancel={() => setShowDeleteModal(false)}
                        onOk={handleDelete}
                    >
                        <p>Are you sure you want to delete this website?</p>
                    </Modal>
                </div>
            </Space>
        </div>
    );
}

export default AdminWebsiteItems;

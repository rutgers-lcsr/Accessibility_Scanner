'use client';
/**
 * Website Admin Items Component
 *
 * This component provides administrative actions for managing a website,
 *
 */

import { Website } from '@/lib/types/website';
import { useUser } from '@/providers/User';
import ScanProgressModal from '@/components/ScanProgressModal';
import { useAlerts } from '@/providers/Alerts';
import { Button, Descriptions, Select, Space } from 'antd';
import { useState } from 'react';
import { useScan } from '@/hooks/useScan';

type Props = {
    website: Website;
    mutate: (website?: Website) => Promise<void>;
};

function WebsiteAdminItems({ website, mutate }: Props) {
    const { addAlert } = useAlerts();
    const [loading, setLoading] = useState(false);
    const { handlerUserApiRequest } = useUser();

    const {
        loading: loadingScan,
        taskId: scanTaskId,
        statusEndpoint: scanStatusEndpoint,
        showProgress: showScanProgress,
        startScan,
        handleScanComplete: onScanComplete,
        handleScanError,
        handleCloseProgress,
    } = useScan({
        websiteId: website.id,
        onComplete: mutate,
    });

    const handleScanComplete = () => {
        onScanComplete();
        mutate();
    };
    const handleUsersChange = async (value: string[] | null) => {
        if (value !== null) {
            setLoading(true);
            try {
                const updatedWebsite = await handlerUserApiRequest<Website>(
                    `/api/websites/${website.id}`,
                    {
                        method: 'PATCH',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ users: value }),
                    }
                );
                mutate(updatedWebsite);
                addAlert('Users updated successfully', 'success');
            } catch (error) {
                addAlert('Failed to update users: ' + (error as Error).message, 'error');
            }

            setLoading(false);
        }
    };

    return (
        <div className="mb-4 rounded-md bg-gray-50 p-4 shadow">
            <Space className="w-full" size={'large'} direction="vertical">
                <Descriptions
                    size="small"
                    column={3}
                    layout="horizontal"
                    title="Website Info"
                    bordered
                >
                    <Descriptions.Item label="Rate Limit">
                        {website.rate_limit}
                        <div className="mt-1 text-xs text-gray-500">
                            The maximum number of pages that can be scanned per month for this
                            website.
                        </div>
                    </Descriptions.Item>
                    <Descriptions.Item label="Last Scanned">
                        {website.last_scanned
                            ? new Date(website.last_scanned).toLocaleString()
                            : 'Never'}
                        <div className="mt-1 text-xs text-gray-500">
                            The last time this website was scanned for accessibility issues.
                        </div>
                    </Descriptions.Item>
                    <Descriptions.Item label="Public">
                        {website.public ? 'Yes' : 'No'}
                        <div className="mt-1 text-xs text-gray-500">
                            Public websites can be viewed by anyone. Private websites can only be
                            viewed by the admins and selected users.
                        </div>
                    </Descriptions.Item>
                    <Descriptions.Item label="Active">
                        {website.active ? 'Yes' : 'No'}
                        <div className="mt-1 text-xs text-gray-500">
                            Inactive websites will not be automatically scanned.
                        </div>
                    </Descriptions.Item>
                    <Descriptions.Item label="Admin">
                        {website.admin}
                        <br />
                        <span className="text-xs text-gray-500"> (You)</span>
                    </Descriptions.Item>
                    <Descriptions.Item label="Users">
                        <Select
                            mode="tags"
                            style={{ minWidth: 300 }}
                            id="users"
                            aria-label="Users"
                            placeholder="Users who can view this website"
                            value={website.users.length > 0 ? website.users : undefined}
                            disabled={loading}
                            onChange={(value) => {
                                // filter out any empty values
                                handleUsersChange(value.filter((v) => v.trim() !== ''));
                            }}
                        />
                        <div className="mt-1 text-xs text-gray-500">
                            Start typing to add users who can view this website. Users and Admin
                            will be notified when a scan finishes. Leave empty to remove all users.
                        </div>
                    </Descriptions.Item>
                    <Descriptions.Item label="Actions">
                        <Button
                            type="primary"
                            loading={loadingScan}
                            onClick={startScan}
                            disabled={loadingScan}
                        >
                            {loadingScan ? 'Scanning...' : 'Scan Website'}
                        </Button>
                    </Descriptions.Item>
                </Descriptions>
            </Space>
            {scanTaskId && scanStatusEndpoint && (
                <ScanProgressModal
                    taskId={scanTaskId}
                    statusEndpoint={scanStatusEndpoint}
                    onComplete={handleScanComplete}
                    onError={handleScanError}
                    visible={showScanProgress}
                    onClose={handleCloseProgress}
                />
            )}
        </div>
    );
}

export default WebsiteAdminItems;

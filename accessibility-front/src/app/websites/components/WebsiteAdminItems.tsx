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
import { Button, Select } from 'antd';
import { useState } from 'react';
import { useScan } from '@/hooks/useScan';
import ExtraStartUrls from './ExtraStartUrls';
import { Field, Legend } from './PanelFields';

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
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                <h2 className="text-lg font-medium text-gray-800">Website Settings</h2>
                <Button
                    type="primary"
                    loading={loadingScan}
                    onClick={() => startScan()}
                    disabled={loadingScan}
                >
                    {loadingScan ? 'Scanning...' : 'Scan Website'}
                </Button>
            </div>

            <div className="grid grid-cols-[repeat(auto-fit,minmax(20rem,1fr))] gap-x-8 gap-y-5">
                <fieldset className="min-w-0">
                    <Legend>Scanning</Legend>
                    <div className="space-y-3">
                        <div className="text-sm text-gray-700">
                            <span className="font-medium">Auto-scan:</span>{' '}
                            {website.active ? `every ${website.rate_limit} days` : 'off'}
                            <span className="ml-2 text-xs text-gray-500">Set by a site admin.</span>
                        </div>
                        <Field id="extra-start-urls" label="Additional start pages">
                            <ExtraStartUrls website={website} mutate={mutate} />
                        </Field>
                    </div>
                </fieldset>

                <fieldset className="min-w-0">
                    <Legend>Access</Legend>
                    <div className="space-y-3">
                        <div className="text-sm text-gray-700">
                            <span className="font-medium">Admin:</span> {website.admin}
                        </div>
                        <Field
                            id="users"
                            label="Additional users"
                            help="They can view this website, triage findings, rescan pages, edit these settings and receive its scan emails. Leave empty to remove all users."
                        >
                            <Select
                                mode="tags"
                                style={{ width: '100%' }}
                                id="users"
                                placeholder="Add usernames"
                                value={website.users.length > 0 ? website.users : undefined}
                                disabled={loading}
                                onChange={(value) => {
                                    // filter out any empty values
                                    handleUsersChange(value.filter((v) => v.trim() !== ''));
                                }}
                            />
                        </Field>
                        <div className="text-sm text-gray-700">
                            <span className="font-medium">Public reports:</span>{' '}
                            {website.public
                                ? 'yes, anyone can view them without signing in.'
                                : 'no, only the admin and the users above.'}
                        </div>
                    </div>
                </fieldset>
            </div>
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

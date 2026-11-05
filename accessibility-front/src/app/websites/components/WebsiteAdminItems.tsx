'use client';
/**
 * Website Admin Items Component
 *
 * This component provides administrative actions for managing a website,
 *
 */

import { Website } from '@/lib/types/website';
import { useUser } from '@/providers/User';
import { useAlerts } from '@/providers/Alerts';
import { Select } from 'antd';
import { useState } from 'react';
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
        <div className="rounded-md bg-gray-50 p-4 shadow">
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
        </div>
    );
}

export default WebsiteAdminItems;

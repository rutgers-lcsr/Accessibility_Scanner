'use client';
import { Website } from '@/lib/types/website';
import { useUser } from '@/providers/User';
import ScanProgressModal from '@/components/ScanProgressModal';
import { useAlerts } from '@/providers/Alerts';
import { useWebsites } from '@/providers/Websites';
import { Button, Input, InputNumber, Modal, Select, Switch } from 'antd';
import TextArea from 'antd/es/input/TextArea';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import useSWR from 'swr';
import { useScan } from '@/hooks/useScan';
import ExtraStartUrls from './ExtraStartUrls';
import { Field, Legend } from './PanelFields';

type Props = {
    website: Website;
    mutate: (website?: Website) => Promise<void>;
};

function AdminItems({ website, mutate }: Props) {
    const router = useRouter();
    const { addAlert } = useAlerts();
    const [loadingActivate, setLoadingActivate] = useState(false);
    const [loadingRateLimit, setLoadingRateLimit] = useState(false);
    const [loadingEmail, setLoadingEmail] = useState(false);
    const [loadingDelete, setLoadingDelete] = useState(false);
    const [loadingShouldEmail, setLoadingShouldEmail] = useState(false);
    const [loadingPublic, setLoadingPublic] = useState(false);
    const [showDeleteModal, setShowDeleteModal] = useState(false);
    const { handlerUserApiRequest } = useUser();
    const { categories } = useWebsites();

    const {
        loading: loadingScan,
        taskId: scanTaskId,
        statusEndpoint: scanStatusEndpoint,
        showProgress: showScanProgress,
        startScan,
        handleScanComplete,
        handleScanError,
        handleCloseProgress,
    } = useScan({
        websiteId: website.id,
        onComplete: () => mutate(),
    });

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
    const handleAdminChange = async (value: string | null) => {
        if (value !== null) {
            setLoadingEmail(true);
            try {
                const updatedWebsite = await handlerUserApiRequest<Website>(
                    `/api/websites/${website.id}`,
                    {
                        method: 'PATCH',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ admin: value }),
                    }
                );
                mutate(updatedWebsite);
                addAlert('Admin user updated successfully', 'success');
            } catch {
                addAlert('Failed to update admin user', 'error');
            }

            setLoadingEmail(false);
        }
    };
    const handleUsersChange = async (value: string[] | null) => {
        if (value !== null) {
            setLoadingEmail(true);
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
    const handleSendEmailUpdate = async () => {
        setLoadingEmail(true);
        try {
            await handlerUserApiRequest<Website>(`/api/websites/email/${website.id}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({}),
            });
            addAlert('Email sent successfully', 'success');
            mutate(); // refresh last_notified
        } catch {
            addAlert('Failed to send email', 'error');
        }
        setLoadingEmail(false);
    };
    const handleDelete = async () => {
        setLoadingDelete(true);
        try {
            await handlerUserApiRequest(`/api/websites/${website.id}/`, {
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

    const handleTagsChange = async (value: string[]) => {
        setLoadingEmail(true);
        try {
            const updatedWebsite = await handlerUserApiRequest<Website>(
                `/api/websites/${website.id}`,
                {
                    method: 'PATCH',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ tags: value.join(',') }),
                }
            );
            mutate(updatedWebsite);
            addAlert('Tags updated successfully', 'success');
        } catch {
            addAlert('Failed to update tags', 'error');
        }
        setLoadingEmail(false);
    };
    const handleCategoriesChange = async (value: string[]) => {
        setLoadingEmail(true);
        try {
            const updatedWebsite = await handlerUserApiRequest<Website>(
                `/api/websites/${website.id}`,
                {
                    method: 'PATCH',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ categories: value.join(',') }),
                }
            );
            mutate(updatedWebsite);
            addAlert('Categories updated successfully', 'success');
        } catch {
            addAlert('Failed to update categories', 'error');
        }
        setLoadingEmail(false);
    };
    const handleDescriptionChange = async (value: string) => {
        setLoadingEmail(true);
        try {
            const updatedWebsite = await handlerUserApiRequest<Website>(
                `/api/websites/${website.id}`,
                {
                    method: 'PATCH',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ description: value }),
                }
            );
            mutate(updatedWebsite);
            addAlert('Description updated successfully', 'success');
        } catch {
            addAlert('Failed to update description', 'error');
        }
        setLoadingEmail(false);
    };

    const { data: allTags } = useSWR(`/api/axe/rules/tags/`, handlerUserApiRequest<string[]>);

    return (
        <div className="mb-4 rounded-md bg-gray-50 p-4 shadow">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                <h2 className="text-lg font-medium text-gray-800">Admin Actions</h2>
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
                        <div className="flex flex-wrap items-center gap-2 text-sm text-gray-700">
                            <Switch
                                id="auto-scan"
                                checked={website.active}
                                loading={loadingActivate}
                                onChange={handleActivate}
                            />
                            <label htmlFor="auto-scan">Auto-scan every</label>
                            <InputNumber
                                id="rate-limit"
                                aria-label="Days between automatic scans"
                                style={{ width: 72 }}
                                min={1}
                                value={website.rate_limit}
                                disabled={!website.active || loadingRateLimit}
                                onChange={async (value) => {
                                    if (value !== null) {
                                        handleRateLimitChange(value.toString());
                                    }
                                }}
                                onPressEnter={async (e) => {
                                    handleRateLimitChange((e.target as HTMLInputElement).value);
                                }}
                            />
                            <span>days</span>
                        </div>
                        <Field id="extra-start-urls" label="Additional start pages">
                            <ExtraStartUrls website={website} mutate={mutate} />
                        </Field>
                    </div>
                </fieldset>

                <fieldset className="min-w-0">
                    <Legend>Tags & details</Legend>
                    <div className="space-y-3">
                        <Field
                            id="tags"
                            label="Active tags"
                            help={
                                <>
                                    <span className="font-semibold">Always applied:</span>{' '}
                                    {website.default_tags.join(', ')}
                                </>
                            }
                        >
                            <Select
                                mode="tags"
                                style={{ width: '100%' }}
                                id="tags"
                                placeholder="Add or select tags"
                                value={Array.from(
                                    new Set([...website.tags, ...website.default_tags])
                                )}
                                options={Array.from(
                                    new Set([
                                        ...website.tags,
                                        ...website.default_tags,
                                        ...(allTags || []),
                                    ])
                                ).map((tag) => ({ label: tag, value: tag }))}
                                disabled={loadingEmail}
                                onChange={handleTagsChange}
                            />
                        </Field>
                        <Field id="categories" label="Categories">
                            <Select
                                mode="tags"
                                style={{ width: '100%' }}
                                id="categories"
                                placeholder="Add or select categories"
                                value={
                                    website.categories.length > 0 ? website.categories : undefined
                                }
                                options={Array.from(
                                    new Set([...(categories || []), ...(website.categories || [])])
                                ).map((category) => ({
                                    label: category,
                                    value: category,
                                }))}
                                disabled={loadingEmail}
                                onChange={handleCategoriesChange}
                            />
                        </Field>
                        <Field id="description" label="Description" help="Press Enter to save.">
                            <TextArea
                                id="description"
                                placeholder="What this website is for"
                                autoSize={{ minRows: 1, maxRows: 4 }}
                                defaultValue={website.description}
                                disabled={loadingEmail}
                                onPressEnter={async (e) => {
                                    e.preventDefault();
                                    handleDescriptionChange((e.target as HTMLInputElement).value);
                                }}
                            />
                        </Field>
                    </div>
                </fieldset>

                <fieldset className="min-w-0">
                    <Legend>Access & notifications</Legend>
                    <div className="space-y-3">
                        <Field id="admin" label="Admin user" help="Press Enter to save.">
                            <Input
                                id="admin"
                                placeholder="Username"
                                defaultValue={website.admin}
                                disabled={loadingEmail}
                                onPressEnter={async (e) => {
                                    handleAdminChange((e.target as HTMLInputElement).value);
                                }}
                            />
                        </Field>
                        <Field
                            id="users"
                            label="Additional users"
                            help="They can view this website and receive its scan emails."
                        >
                            <Select
                                mode="tags"
                                style={{ width: '100%' }}
                                id="users"
                                placeholder="Add usernames"
                                value={website.users.length > 0 ? website.users : undefined}
                                disabled={loadingEmail}
                                onChange={(value) => {
                                    handleUsersChange(value.filter((v) => v.trim() !== ''));
                                }}
                            />
                        </Field>
                        <div className="flex flex-wrap items-center gap-2 text-sm text-gray-700">
                            <Switch
                                id="public"
                                checked={website.public}
                                loading={loadingPublic}
                                onChange={handleChangePublic}
                            />
                            <label htmlFor="public">Public reports</label>
                            <span className="text-xs text-gray-500">
                                Anyone can view them without signing in.
                            </span>
                        </div>
                        <div className="flex flex-wrap items-center gap-2 text-sm text-gray-700">
                            <Switch
                                id="should-email"
                                checked={website.should_email}
                                loading={loadingShouldEmail}
                                onChange={handleShouldEmailChange}
                            />
                            <label htmlFor="should-email">
                                Include this website in the owner digest emails
                            </label>
                        </div>
                        <div className="flex flex-wrap items-center gap-3 text-xs text-gray-500">
                            <Button
                                size="small"
                                onClick={handleSendEmailUpdate}
                                loading={loadingEmail}
                            >
                                Send digest now
                            </Button>
                            <span>
                                Last notified:{' '}
                                {website.last_notified
                                    ? new Date(website.last_notified).toLocaleString()
                                    : 'Never'}
                            </span>
                        </div>
                    </div>
                </fieldset>
            </div>

            <div className="mt-5 flex flex-wrap items-center justify-between gap-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm">
                <div>
                    <span className="font-medium text-red-700">Delete website.</span>{' '}
                    <span className="text-gray-600">
                        Removes this website and all of its reports permanently.
                    </span>
                </div>
                <Button
                    danger
                    size="small"
                    onClick={() => setShowDeleteModal(true)}
                    loading={loadingDelete}
                >
                    Delete Website
                </Button>
            </div>
            <Modal
                title="Confirm Deletion"
                open={showDeleteModal}
                onCancel={() => setShowDeleteModal(false)}
                onOk={handleDelete}
            >
                <p>Are you sure you want to delete this website?</p>
            </Modal>
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

export default AdminItems;

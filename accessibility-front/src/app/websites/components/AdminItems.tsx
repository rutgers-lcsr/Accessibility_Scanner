'use client';
import { Website } from '@/lib/types/website';
import { useUser } from '@/providers/User';
import ScanProgressModal from '@/components/ScanProgressModal';
import { useAlerts } from '@/providers/Alerts';
import { useWebsites } from '@/providers/Websites';
import {
    Typography,
    Button,
    Divider,
    Flex,
    Input,
    InputNumber,
    Modal,
    Select,
    Space,
    Tooltip,
} from 'antd';
import { InfoCircleOutlined } from '@ant-design/icons';
import TextArea from 'antd/es/input/TextArea';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import useSWR from 'swr';
import { useScan } from '@/hooks/useScan';

const { Text } = Typography;

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
        onComplete: mutate,
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
            <Space className="w-full" size="large" direction="vertical">
                <div className="text-lg font-medium text-gray-800">Admin Actions</div>

                {/* Scan and Activation Section */}
                <Divider orientation="left" orientationMargin={0}>
                    <span>Scan & Activation</span>
                </Divider>
                <div>
                    <div className="text-sm font-medium text-gray-700 mb-3">Scanning</div>
                    <Flex gap="12px" align="center" wrap="wrap">
                        <Tooltip title="Manually trigger a scan for this website. You will be notified when the scan is complete.">
                            <Button
                                type="primary"
                                loading={loadingScan}
                                onClick={startScan}
                                disabled={loadingScan}
                            >
                                {loadingScan ? 'Scanning...' : 'Scan Website'}
                            </Button>
                        </Tooltip>
                        <Tooltip
                            title={
                                website.active
                                    ? 'Disable automatic scanning for this website.'
                                    : 'Enable automatic scanning for this website.'
                            }
                        >
                            <Button
                                loading={loadingActivate}
                                type={website.active ? 'primary' : 'default'}
                                onClick={handleActivate}
                            >
                                {website.active ? 'Auto-Scan: ON' : 'Auto-Scan: OFF'}
                            </Button>
                        </Tooltip>
                        <Tooltip title="Set how often this website can be scanned (in days). Only applies to automatic scans.">
                            <InputNumber
                                disabled={!website.active || loadingRateLimit}
                                addonBefore="Rate Limit (days)"
                                aria-label="Rate Limit in Days"
                                min={1}
                                defaultValue={website.rate_limit}
                                value={website.rate_limit}
                                onChange={async (value) => {
                                    if (value !== null) {
                                        handleRateLimitChange(value.toString());
                                    }
                                }}
                                onPressEnter={async (e) => {
                                    handleRateLimitChange((e.target as HTMLInputElement).value);
                                }}
                            />
                        </Tooltip>
                    </Flex>
                </div>

                {/* Website Tags and Categories Section */}
                <Divider orientation="left" orientationMargin={0}>
                    <span>Tags & Categories</span>
                </Divider>
                <Flex gap="16px" align="start" wrap="wrap">
                    {/* Tags */}
                    <div style={{ minWidth: 320, flex: 1 }}>
                        <label
                            htmlFor="tags"
                            className="block text-sm font-medium text-gray-700 mb-2"
                        >
                            Active Tags
                        </label>
                        <Tooltip title="Tags applied to this website, used in addition to the default tags for which rule sets to apply. Default tags are automatically applied to all websites and cannot be removed here.">
                            <Select
                                mode="tags"
                                style={{ width: '100%' }}
                                id="tags"
                                aria-label="Tags"
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
                        </Tooltip>
                        <div className="text-xs text-gray-500 mt-1">
                            <span className="font-semibold">Default:</span>{' '}
                            {website.default_tags.join(', ')}
                        </div>
                    </div>
                    {/* Categories */}
                    <div style={{ minWidth: 320, flex: 1 }}>
                        <label
                            htmlFor="categories"
                            className="block text-sm font-medium text-gray-700 mb-2"
                        >
                            Categories
                        </label>
                        <Tooltip title="Categories are used to classify websites. For use in filtering and organization.">
                            <Select
                                mode="tags"
                                style={{ width: '100%' }}
                                id="categories"
                                aria-label="Categories"
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
                            ></Select>
                        </Tooltip>
                    </div>
                    <div style={{ minWidth: 320, flex: 1 }}>
                        <label
                            htmlFor="description"
                            className="block text-sm font-medium text-gray-700 mb-2"
                        >
                            Description
                        </label>
                        <Tooltip title="A brief description of the website's purpose or content.">
                            <TextArea
                                style={{ width: '100%' }}
                                id="description"
                                aria-label="Description"
                                placeholder="Website Description"
                                defaultValue={website.description}
                                disabled={loadingEmail}
                                onPressEnter={async (e) => {
                                    handleDescriptionChange((e.target as HTMLInputElement).value);
                                }}
                            />
                        </Tooltip>
                    </div>
                </Flex>

                {/* Admin & Users Section */}
                <Divider orientation="left" orientationMargin={0}>
                    <span>Admin & Users</span>
                </Divider>
                <div>
                    <div className="text-sm font-medium text-gray-700 mb-3">User Management</div>
                    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                        <Flex gap="12px" align="center" wrap="wrap">
                            <label
                                htmlFor="admin"
                                className="text-sm font-medium text-gray-700"
                                style={{ minWidth: 100 }}
                            >
                                Admin User:
                            </label>
                            <Tooltip title="The user who is an Website Admin for this website.">
                                <Input
                                    style={{ minWidth: 280, maxWidth: 400 }}
                                    id="admin"
                                    aria-label="Admin User"
                                    placeholder="Admin User Email"
                                    type="text"
                                    defaultValue={website.admin}
                                    disabled={loadingEmail}
                                    onPressEnter={async (e) => {
                                        handleAdminChange((e.target as HTMLInputElement).value);
                                    }}
                                />
                            </Tooltip>
                        </Flex>
                        <Flex gap="12px" align="center" wrap="wrap">
                            <label
                                htmlFor="users"
                                className="text-sm font-medium text-gray-700"
                                style={{ minWidth: 100 }}
                            >
                                Additional Users:
                            </label>
                            <Tooltip title="Users who are allowed to view this website. Users and Admin will be notified when a scan finishes. Only if email notifications are enabled.">
                                <Select
                                    mode="tags"
                                    style={{ minWidth: 280, maxWidth: 600 }}
                                    id="users"
                                    aria-label="Users"
                                    placeholder="Users who can view this website"
                                    value={website.users.length > 0 ? website.users : undefined}
                                    disabled={loadingEmail}
                                    onChange={(value) => {
                                        handleUsersChange(value.filter((v) => v.trim() !== ''));
                                    }}
                                />
                            </Tooltip>
                        </Flex>
                    </Space>
                </div>

                {/* Email & Public Section */}

                <Divider orientation="left" orientationMargin={0}>
                    <span>Email & Public Access</span>
                </Divider>

                {/* Info Banner */}
                <div className="rounded-lg bg-blue-50 border border-blue-200 p-3">
                    <Space direction="horizontal" size={8} align="start">
                        <InfoCircleOutlined className="text-blue-600 mt-0.5" />
                        <Text type="secondary" className="text-sm">
                            <strong>Email Notification Thresholds:</strong> Users are notified when
                            a scan detects at least <strong>1 critical</strong>,{' '}
                            <strong>5 serious</strong>, <strong>10 moderate</strong>,{' '}
                            <strong>10 minor</strong> issues, or when{' '}
                            <strong>total issues ≥ 15</strong>.
                        </Text>
                    </Space>
                </div>

                {/* Email Controls */}
                <div>
                    <div className="text-sm font-medium text-gray-700 mb-3">
                        Email Notifications
                    </div>
                    <Flex gap="12px" align="center" wrap="wrap">
                        <Tooltip
                            title={
                                website.should_email
                                    ? 'Disable automatic email notifications for this website.'
                                    : 'Enable automatic email notifications for this website.'
                            }
                        >
                            <Button
                                type={website.should_email ? 'primary' : 'default'}
                                loading={loadingShouldEmail}
                                onClick={() => handleShouldEmailChange(!website.should_email)}
                                icon={<InfoCircleOutlined />}
                            >
                                {website.should_email
                                    ? 'Email Notifications: ON'
                                    : 'Email Notifications: OFF'}
                            </Button>
                        </Tooltip>
                        <Tooltip title="Send the latest report email to all users immediately, regardless of notification settings or thresholds.">
                            <Button
                                onClick={handleSendEmailUpdate}
                                loading={loadingEmail}
                                type="dashed"
                            >
                                Send Report Email Now
                            </Button>
                        </Tooltip>
                    </Flex>
                </div>

                {/* Public Access Controls */}
                <div>
                    <div className="text-sm font-medium text-gray-700 mb-3">Public Access</div>
                    <Tooltip
                        title={
                            website.public
                                ? "Make this website's reports private (only accessible to authorized users)."
                                : "Make this website's reports publicly accessible."
                        }
                    >
                        <Button
                            type={website.public ? 'primary' : 'default'}
                            loading={loadingPublic}
                            onClick={() => handleChangePublic(!website.public)}
                            danger={website.public}
                        >
                            {website.public ? 'Public Access: ON' : 'Public Access: OFF'}
                        </Button>
                    </Tooltip>
                </div>

                {/* Danger Zone Section */}
                <Divider orientation="left" orientationMargin={0}>
                    <span className="text-red-600">Danger Zone</span>
                </Divider>
                <div className="rounded-lg bg-red-50 border border-red-200 p-4">
                    <Flex justify="space-between" align="center" wrap="wrap" gap="12px">
                        <div>
                            <div className="text-sm font-medium text-gray-900 mb-1">
                                Delete Website
                            </div>
                            <div className="text-xs text-gray-600">
                                Once deleted, this website and all its reports will be permanently
                                removed.
                            </div>
                        </div>
                        <Button
                            danger
                            onClick={() => setShowDeleteModal(true)}
                            loading={loadingDelete}
                        >
                            Delete Website
                        </Button>
                    </Flex>
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

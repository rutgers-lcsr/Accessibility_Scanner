'use client';
import EditableInput from '@/components/EditableInput';
import PageLoading from '@/components/PageLoading';
import { useSettings } from '@/providers/Settings';
import { InfoCircleOutlined } from '@ant-design/icons';
import { Card, Select } from 'antd';
import { useState } from 'react';

function Settings() {
    const { settings, all_tags, updateSettings } = useSettings();
    const [loading, setLoading] = useState(false);
    const handleSave = async (key: string, newValue: string | number) => {
        setLoading(true);
        await updateSettings({ [key]: newValue });
        setLoading(false);
    };

    if (!settings) {
        return <PageLoading />;
    }
    if (!all_tags) {
        return <PageLoading />;
    }

    const selectedTags = settings.default_tags
        ? settings.default_tags.split(',').filter(Boolean)
        : [];

    return (
        <div className="flex justify-center items-start min-h-screen">
            <Card
                loading={loading}
                title="Application Settings"
                className="w-full max-w-xl shadow-lg"
                extra={
                    <div>
                        <InfoCircleOutlined /> Click to edit
                    </div>
                }
            >
                <EditableInput
                    label="Rate Limit (Days between Scans)"
                    type="number"
                    value={settings?.default_rate_limit || ''}
                    onChange={(value) => handleSave('default_rate_limit', value)}
                />
                <div className="text-sm text-gray-500">
                    Default rate limit in days between scans for new websites, this can be
                    overridden per website.
                </div>
                <div className="my-4" />
                <label className="block mb-2 font-bold" htmlFor="default_tags">
                    Default Tags (for all scans)
                </label>
                <Select
                    id="default_tags"
                    mode="tags"
                    style={{ width: '100%' }}
                    value={selectedTags || undefined}
                    onChange={async (value) => {
                        const stringValue = value.join(','); // Ensure value is treated as array of strings
                        await handleSave('default_tags', stringValue);
                    }}
                    loading={loading}
                >
                    {(all_tags || []).map((tag) => (
                        <Select.Option key={tag} value={tag} label={<span>{tag}</span>}>
                            {tag}
                        </Select.Option>
                    ))}
                </Select>
                <div className="text-sm text-gray-500">
                    Select default tags for all new scans, these can be modified per website,
                    default tags will run every time, you can not remove default tags from a website
                    unless you change them here.
                </div>
                <div className="my-4" />
                <label className="block mb-2 font-bold" htmlFor="default_should_auto_scan">
                    Default Auto Scan New Websites
                </label>
                <Select
                    id="default_should_auto_scan"
                    value={
                        settings?.default_should_auto_scan?.toString() === 'true' ? 'true' : 'false'
                    }
                    onChange={(value) =>
                        handleSave('default_should_auto_scan', value === 'true' ? 'true' : 'false')
                    }
                    options={[
                        { label: 'Enabled', value: 'true' },
                        { label: 'Disabled', value: 'false' },
                    ]}
                />
                <div className="text-sm text-gray-500">
                    Should new websites be automatically scanned when added, this can be overridden
                    per website.
                </div>
                <label className="block mb-2 font-bold" htmlFor="default_should_auto_activate">
                    Default Auto Activate New Websites
                </label>
                <Select
                    id="default_should_auto_activate"
                    value={
                        settings?.default_should_auto_activate?.toString() === 'true'
                            ? 'true'
                            : 'false'
                    }
                    onChange={(value) =>
                        handleSave(
                            'default_should_auto_activate',
                            value === 'true' ? 'true' : 'false'
                        )
                    }
                    options={[
                        { label: 'Enabled', value: 'true' },
                        { label: 'Disabled', value: 'false' },
                    ]}
                />
                <div className="text-sm text-gray-500">
                    Should new websites be automatically activated for automatic scanning per rate
                    limit when added, this can be overridden per website.
                </div>
                <div className="my-4" />
                <label className="block mb-2 font-bold" htmlFor="default_notify_on_completion">
                    Default Notify on Scan Completion
                </label>
                <Select
                    id="default_notify_on_completion"
                    value={
                        settings?.default_notify_on_completion?.toString() === 'true'
                            ? 'true'
                            : 'false'
                    }
                    onChange={(value) =>
                        handleSave(
                            'default_notify_on_completion',
                            value === 'true' ? 'true' : 'false'
                        )
                    }
                    options={[
                        { label: 'Enabled', value: 'true' },
                        { label: 'Disabled', value: 'false' },
                    ]}
                />
                <div className="text-sm text-gray-500">
                    Should users be notified by email when a scan completes, this can be overridden
                    per website.
                </div>
                <div className="my-4" />
                <EditableInput
                    id="default_email_domain"
                    label="Default Email Domain"
                    type="text"
                    placeholder='e.g. "example.com"'
                    value={settings?.default_email_domain || ''}
                    onChange={(value) => handleSave('default_email_domain', value)}
                    validate={(value) => {
                        if (value && !/^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(value)) {
                            return 'Invalid domain format';
                        }
                        return null;
                    }}
                />
                <div className="text-sm text-gray-500">
                    Default email domain for users. Users will be sent emails using their username
                    and this domain, e.g. user@example.com. Leaving it blank will cause users to not
                    be added. Note: Not implemented yet. Assumes all users share the same email
                    domain. usually the university domain.
                </div>
            </Card>
        </div>
    );
}

export default Settings;

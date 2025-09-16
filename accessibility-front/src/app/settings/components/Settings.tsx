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
                title="Application Settings"
                className="w-full max-w-xl shadow-lg"
                extra={
                    <div>
                        <InfoCircleOutlined /> Double click to edit
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
            </Card>
        </div>
    );
}

export default Settings;

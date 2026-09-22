'use client';
import EditableInput from '@/components/EditableInput';
import PageLoading from '@/components/PageLoading';
import { useSettings } from '@/providers/Settings';
import { InfoCircleOutlined } from '@ant-design/icons';
import { Card, Flex, Select } from 'antd';
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
        <>
            <div className="w-full">
                <Flex align="center" justify="center" className="w-full">
                    <Card
                        loading={loading}
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
                        <EditableInput
                            label="Pages scanned at once (per website scan)"
                            type="number"
                            value={settings?.scan_page_concurrency || ''}
                            onChange={(value) => handleSave('scan_page_concurrency', value)}
                        />
                        <div className="text-sm text-gray-500">
                            How many pages of a website the scanner audits concurrently. Each page
                            is a browser tab; lower this if the worker runs out of memory, raise it
                            for faster scans of large sites.
                        </div>
                        <div className="my-4" />
                        <EditableInput
                            label="Maximum pages per website scan"
                            type="number"
                            value={settings?.max_pages || ''}
                            onChange={(value) => handleSave('max_pages', value)}
                        />
                        <div className="text-sm text-gray-500">
                            A crawl stops discovering new pages once this many have been found, so
                            calendars and paginated listings cannot run a scan forever.
                        </div>
                        <div className="my-4" />
                        <EditableInput
                            label="Maximum link depth"
                            type="number"
                            value={settings?.max_depth || ''}
                            onChange={(value) => handleSave('max_depth', value)}
                        />
                        <div className="text-sm text-gray-500">
                            How many links away from the start page the crawler follows (0 scans
                            only the start page).
                        </div>
                        <div className="my-4" />
                        <EditableInput
                            label="Delay between page requests (ms)"
                            type="number"
                            value={settings?.crawl_delay_ms || ''}
                            onChange={(value) => handleSave('crawl_delay_ms', value)}
                        />
                        <div className="text-sm text-gray-500">
                            Pause before each page request so small sites are not overwhelmed. Pages
                            listed as disallowed for LCSRAccessibility (or all agents) in the
                            site&apos;s robots.txt are skipped.
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
                            Select default tags for all new scans, these can be modified per
                            website, default tags will run every time, you can not remove default
                            tags from a website unless you change them here.
                        </div>
                        <div className="my-4" />
                        <label className="block mb-2 font-bold" htmlFor="default_should_auto_scan">
                            Default Auto Scan New Websites
                        </label>
                        <Select
                            id="default_should_auto_scan"
                            value={
                                settings?.default_should_auto_scan?.toString() === 'true'
                                    ? 'true'
                                    : 'false'
                            }
                            onChange={(value) =>
                                handleSave(
                                    'default_should_auto_scan',
                                    value === 'true' ? 'true' : 'false'
                                )
                            }
                            options={[
                                { label: 'Enabled', value: 'true' },
                                { label: 'Disabled', value: 'false' },
                            ]}
                        />
                        <div className="text-sm text-gray-500">
                            Should new websites be automatically scanned when added, this can be
                            overridden per website.
                        </div>
                        <label
                            className="block mb-2 font-bold"
                            htmlFor="default_should_auto_activate"
                        >
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
                            Should new websites be automatically activated for automatic scanning
                            per rate limit when added, this can be overridden per website.
                        </div>
                        <div className="my-4" />
                        <label
                            className="block mb-2 font-bold"
                            htmlFor="default_notify_on_completion"
                        >
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
                            Should users be notified by email when a scan completes, this can be
                            overridden per website.
                        </div>
                        <label className="block mb-2 font-bold" htmlFor="admin_digest_enabled">
                            Weekly Digest To Site Admins
                        </label>
                        <Select
                            id="admin_digest_enabled"
                            value={
                                settings?.admin_digest_enabled?.toString() === 'false'
                                    ? 'false'
                                    : 'true'
                            }
                            onChange={(value) =>
                                handleSave(
                                    'admin_digest_enabled',
                                    value === 'true' ? 'true' : 'false'
                                )
                            }
                            options={[
                                { label: 'Enabled', value: 'true' },
                                { label: 'Disabled', value: 'false' },
                            ]}
                        />
                        <div className="text-sm text-gray-500">
                            A weekly email to site admins summarising all websites: totals, biggest
                            movers, failing and never-scanned websites. The day and hour are set on
                            the server.
                        </div>
                        <div className="my-4" />
                        <label className="block mb-2 font-bold" htmlFor="retention_enabled">
                            Report Retention
                        </label>
                        <Select
                            id="retention_enabled"
                            value={
                                settings?.retention_enabled?.toString() === 'true'
                                    ? 'true'
                                    : 'false'
                            }
                            onChange={(value) =>
                                handleSave('retention_enabled', value === 'true' ? 'true' : 'false')
                            }
                            options={[
                                { label: 'Enabled', value: 'true' },
                                { label: 'Disabled', value: 'false' },
                            ]}
                        />
                        <div className="text-sm text-gray-500">
                            Nightly clean-up of old reports. Off by default: run{' '}
                            <code>flask maintenance retention --dry-run</code> on the server first
                            and read the plan. A page&apos;s latest report is never deleted.
                        </div>
                        <div className="my-4" />
                        <EditableInput
                            label="Days kept in full"
                            type="number"
                            value={settings?.retention_keep_days || ''}
                            onChange={(value) => handleSave('retention_keep_days', value)}
                        />
                        <div className="text-sm text-gray-500">
                            Every report younger than this is kept with its screenshot.
                        </div>
                        <div className="my-4" />
                        <EditableInput
                            label="Days kept as one report per month"
                            type="number"
                            value={settings?.retention_max_days || ''}
                            onChange={(value) => handleSave('retention_max_days', value)}
                        />
                        <div className="text-sm text-gray-500">
                            Older than the full window and younger than this, one report per month
                            survives without its screenshot; anything older is deleted.
                        </div>
                        <div className="my-4" />
                        <EditableInput
                            label="PDF checks per scan"
                            type="number"
                            value={settings?.document_checks_per_scan || ''}
                            onChange={(value) => handleSave('document_checks_per_scan', value)}
                        />
                        <div className="text-sm text-gray-500">
                            How many of a website&apos;s own PDFs a scan downloads and checks for
                            tagging, title and language (0 switches the checks off; links are still
                            listed).
                        </div>
                        <div className="my-4" />
                        <EditableInput
                            label="Largest PDF to check (MB)"
                            type="number"
                            value={settings?.document_max_size_mb || ''}
                            onChange={(value) => handleSave('document_max_size_mb', value)}
                        />
                        <div className="my-4" />
                        <EditableInput
                            label="Days between PDF re-checks"
                            type="number"
                            value={settings?.document_recheck_days || ''}
                            onChange={(value) => handleSave('document_recheck_days', value)}
                        />
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
                            Default email domain for users. Users will be sent emails using their
                            username and this domain, e.g. user@example.com. Leaving it blank will
                            cause users to not be added. Assumes all users share the same email
                            domain, usually the university domain.
                        </div>
                    </Card>
                </Flex>
            </div>
        </>
    );
}

export default Settings;

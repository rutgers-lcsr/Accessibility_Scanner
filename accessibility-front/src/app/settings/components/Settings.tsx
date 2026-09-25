'use client';
import PageLoading from '@/components/PageLoading';
import { APIError } from '@/lib/api';
import { useUrlFilters } from '@/lib/urlFilters';
import { Field } from '@/app/websites/components/PanelFields';
import { useAlerts } from '@/providers/Alerts';
import { SettingKey, useSettings } from '@/providers/Settings';
import { Grid, Input, InputNumber, Select, Switch, Tabs } from 'antd';
import { ReactNode, useState } from 'react';

type Setting = {
    key: SettingKey;
    label: string;
    help?: ReactNode;
    kind: 'switch' | 'number' | 'text' | 'tags';
    min?: number; // the backend's lower bound (blueprints/settings.py)
    placeholder?: string;
};

type Section = { key: string; label: string; intro: string; settings: Setting[] };

const SECTIONS: Section[] = [
    {
        key: 'scanning',
        label: 'Scanning',
        intro: 'How the crawler finds and audits pages.',
        settings: [
            {
                key: 'default_rate_limit',
                label: 'Days between scans',
                kind: 'number',
                min: 1,
                help: 'How often a website with Auto-scan on is rescanned. Each website can override it.',
            },
            {
                key: 'scan_page_concurrency',
                label: 'Pages scanned at once',
                kind: 'number',
                min: 1,
                help: 'Each page is a browser tab. Lower it if the worker runs out of memory; raise it for faster scans of large sites.',
            },
            {
                key: 'max_pages',
                label: 'Maximum pages per scan',
                kind: 'number',
                min: 1,
                help: "A crawl stops finding new pages after this many, so calendars and paginated listings can't run forever.",
            },
            {
                key: 'max_depth',
                label: 'Maximum link depth',
                kind: 'number',
                min: 0,
                help: 'How many links from the start page the crawler follows. 0 scans only the start page.',
            },
            {
                key: 'crawl_delay_ms',
                label: 'Delay between page requests (ms)',
                kind: 'number',
                min: 0,
                help: "A pause before each request so small sites aren't overwhelmed. Pages robots.txt disallows for LCSRAccessibility (or all agents) are skipped.",
            },
            {
                key: 'default_tags',
                label: 'Default tags',
                kind: 'tags',
                help: "The rule tags every scan runs. A website can add tags but can't remove these.",
            },
        ],
    },
    {
        key: 'new-websites',
        label: 'New websites',
        intro: 'What a website starts with when it is added. Each website can change these afterwards.',
        settings: [
            {
                key: 'default_should_auto_scan',
                label: 'Scan when added',
                kind: 'switch',
                help: 'Run one scan as soon as the website is added.',
            },
            {
                key: 'default_should_auto_activate',
                label: 'Turn on Auto-scan',
                kind: 'switch',
                help: 'Rescan the website every "Days between scans". Off means it is scanned only on request.',
            },
            {
                key: 'default_notify_on_completion',
                label: 'Include in owner digests',
                kind: 'switch',
                help: 'Switch on "Include this website in the owner digest emails" for the new website.',
            },
        ],
    },
    {
        key: 'emails',
        label: 'Emails',
        intro: 'Digests, reminders and escalation.',
        settings: [
            {
                key: 'owner_digest_enabled',
                label: 'Owner digests',
                kind: 'switch',
                help: 'One daily email per website owner or member, covering their websites that have digests switched on. Sent only when something changed or a reminder is due; a website with no issues counts only when something on it got fixed.',
            },
            {
                key: 'reminder_after_days',
                label: 'Remind after (days without activity)',
                kind: 'number',
                min: 1,
                help: 'A website with open critical or serious issues and no verdicts or fixes this long after its last email gets a firmer reminder, once per period.',
            },
            {
                key: 'escalate_after_days',
                label: 'Escalate after (days without activity)',
                kind: 'number',
                min: 1,
                help: "After this long without activity the website admin's reminder is also sent to the escalation email.",
            },
            {
                key: 'escalation_email',
                label: 'Escalation email',
                kind: 'text',
                help: 'Leave it empty to never escalate.',
            },
            {
                key: 'admin_digest_enabled',
                label: 'Weekly digest to site admins',
                kind: 'switch',
                help: 'Totals, biggest movers, and failing or never-scanned websites. The day and hour are set on the server.',
            },
        ],
    },
    {
        key: 'retention',
        label: 'Report retention',
        intro: "Nightly clean-up of old reports. A page's latest report is never deleted.",
        settings: [
            {
                key: 'retention_enabled',
                label: 'Nightly clean-up',
                kind: 'switch',
                help: (
                    <>
                        Off by default. Run <code>flask maintenance retention --dry-run</code> on
                        the server and read the plan before switching it on.
                    </>
                ),
            },
            {
                key: 'retention_keep_days',
                label: 'Days kept in full',
                kind: 'number',
                min: 1,
                help: 'Reports younger than this keep their screenshot.',
            },
            {
                key: 'retention_max_days',
                label: 'Days kept as one report per month',
                kind: 'number',
                min: 1,
                help: 'Between the two windows one report per month survives, without its screenshot. Anything older is deleted.',
            },
        ],
    },
    {
        key: 'pdfs',
        label: 'PDF checks',
        intro: "Checks of a website's own PDFs for tagging, title and language.",
        settings: [
            {
                key: 'document_checks_per_scan',
                label: 'PDFs checked per scan',
                kind: 'number',
                min: 0,
                help: '0 turns the checks off; the links are still listed.',
            },
            {
                key: 'document_max_size_mb',
                label: 'Largest PDF to check (MB)',
                kind: 'number',
                min: 1,
                help: 'A bigger file is marked too large and not downloaded.',
            },
            {
                key: 'document_recheck_days',
                label: 'Days between PDF re-checks',
                kind: 'number',
                min: 1,
                help: 'A PDF checked more recently than this is skipped; unchecked PDFs go first.',
            },
        ],
    },
    {
        key: 'users',
        label: 'Users',
        intro: 'How people added to websites get an email address.',
        settings: [
            {
                key: 'default_email_domain',
                label: 'Default email domain',
                kind: 'text',
                placeholder: 'e.g. rutgers.edu',
                help: 'Users are emailed at their username at this domain, e.g. netid@rutgers.edu. If it is blank, users are not added.',
            },
        ],
    },
];

type SaveFn = (key: SettingKey, value: string) => Promise<boolean>;

// Numbers and text save on Enter or when the field loses focus, and only if they changed.
// The parent keys each control by its saved value, so a failed save resets the draft.
function DraftNumber({ setting, value, save }: { setting: Setting; value: string; save: SaveFn }) {
    const [draft, setDraft] = useState<number | null>(value === '' ? null : Number(value));
    const [saving, setSaving] = useState(false);
    const commit = async () => {
        if (draft === null || String(draft) === value) {
            setDraft(value === '' ? null : Number(value));
            return;
        }
        setSaving(true);
        if (!(await save(setting.key, String(draft)))) setDraft(Number(value));
        setSaving(false);
    };
    return (
        <InputNumber
            id={setting.key}
            min={setting.min}
            precision={0}
            value={draft}
            disabled={saving}
            onChange={setDraft}
            onBlur={commit}
            onPressEnter={commit}
            style={{ width: 140 }}
        />
    );
}

function DraftText({ setting, value, save }: { setting: Setting; value: string; save: SaveFn }) {
    const [draft, setDraft] = useState(value);
    const [saving, setSaving] = useState(false);
    const commit = async () => {
        if (draft.trim() === value) return;
        setSaving(true);
        if (!(await save(setting.key, draft.trim()))) setDraft(value);
        setSaving(false);
    };
    return (
        <Input
            id={setting.key}
            value={draft}
            placeholder={setting.placeholder}
            disabled={saving}
            onChange={(e) => setDraft(e.target.value)}
            onBlur={commit}
            onPressEnter={commit}
            className="max-w-sm"
        />
    );
}

function SettingRow({
    setting,
    value,
    tags,
    save,
}: {
    setting: Setting;
    value: string;
    tags: string[];
    save: SaveFn;
}) {
    const [saving, setSaving] = useState(false);

    if (setting.kind === 'switch') {
        return (
            <div>
                <div className="flex items-center gap-3">
                    <Switch
                        id={setting.key}
                        checked={value === 'true'}
                        loading={saving}
                        onChange={async (checked) => {
                            setSaving(true);
                            await save(setting.key, checked ? 'true' : 'false');
                            setSaving(false);
                        }}
                    />
                    <label htmlFor={setting.key} className="text-sm font-medium text-gray-700">
                        {setting.label}
                    </label>
                </div>
                {setting.help && (
                    <div className="mt-1 text-xs text-gray-500 md:pl-14">{setting.help}</div>
                )}
            </div>
        );
    }

    let control: ReactNode;
    if (setting.kind === 'number') {
        control = <DraftNumber key={value} setting={setting} value={value} save={save} />;
    } else if (setting.kind === 'text') {
        control = <DraftText key={value} setting={setting} value={value} save={save} />;
    } else {
        control = (
            <Select
                id={setting.key}
                mode="tags"
                className="w-full max-w-xl"
                value={value
                    .split(',')
                    .map((tag) => tag.trim())
                    .filter(Boolean)}
                loading={saving}
                disabled={saving}
                options={tags.map((tag) => ({ label: tag, value: tag }))}
                onChange={async (next: string[]) => {
                    setSaving(true);
                    await save(setting.key, next.join(','));
                    setSaving(false);
                }}
            />
        );
    }
    return (
        <Field id={setting.key} label={setting.label} help={setting.help}>
            {control}
        </Field>
    );
}

function Settings() {
    const { settings, all_tags, updateSettings } = useSettings();
    const { addAlert } = useAlerts();
    const { params, setFilters } = useUrlFilters();
    const screens = Grid.useBreakpoint();
    const [active, setActive] = useState(params.get('section') ?? SECTIONS[0].key);

    if (!settings || !all_tags) {
        return <PageLoading />;
    }

    const labelOf = (key: SettingKey) =>
        SECTIONS.flatMap((section) => section.settings).find((s) => s.key === key)?.label ?? key;

    const save: SaveFn = async (key, value) => {
        try {
            await updateSettings({ [key]: value });
            addAlert(`Saved ${labelOf(key).toLowerCase()}`, 'success');
            return true;
        } catch (error) {
            // The API says "<key> <reason>"; name the setting by its label instead.
            const reason =
                error instanceof APIError ? error.message.replace(`${key} `, '') : 'save failed';
            addAlert(`${labelOf(key)}: ${reason}`, 'error');
            return false;
        }
    };

    return (
        <div className="rounded-lg bg-white p-4 shadow">
            <Tabs
                tabPlacement={screens.md ? 'start' : 'top'}
                activeKey={SECTIONS.some((s) => s.key === active) ? active : SECTIONS[0].key}
                onChange={(key) => {
                    setActive(key);
                    setFilters({ section: key === SECTIONS[0].key ? null : key });
                }}
                items={SECTIONS.map((section) => ({
                    key: section.key,
                    label: section.label,
                    children: (
                        <section aria-labelledby={`settings-${section.key}`} className="max-w-3xl">
                            <h2
                                id={`settings-${section.key}`}
                                className="text-lg font-semibold text-gray-800"
                                style={{ marginBottom: 4 }}
                            >
                                {section.label}
                            </h2>
                            <p className="mb-6 text-sm text-gray-600">{section.intro}</p>
                            <div className="space-y-6">
                                {section.settings.map((setting) => (
                                    <SettingRow
                                        key={setting.key}
                                        setting={setting}
                                        value={String(settings[setting.key] ?? '')}
                                        tags={all_tags}
                                        save={save}
                                    />
                                ))}
                            </div>
                        </section>
                    ),
                }))}
            />
        </div>
    );
}

export default Settings;

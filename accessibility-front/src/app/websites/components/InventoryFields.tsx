'use client';
import {
    AUDIENCE_LABELS,
    CRITICALITY_LABELS,
    LIFECYCLE_LABELS,
    Website,
    WebsiteAudience,
    WebsiteCriticality,
    WebsiteLifecycle,
} from '@/lib/types/website';
import { useAlerts } from '@/providers/Alerts';
import { useUser } from '@/providers/User';
import { AutoComplete, Input, Select } from 'antd';
import { useState } from 'react';
import useSWR from 'swr';
import { Field, Legend } from './PanelFields';

type Props = {
    website: Website;
    mutate: (website?: Website) => Promise<void>;
    // Site admins also set lifecycle, sunset date and criticality.
    isAdmin: boolean;
};

const options = <T extends string>(labels: Record<T, string>) =>
    (Object.keys(labels) as T[]).map((value) => ({ value, label: labels[value] }));

// Who is accountable for a website and where it is in its life: the inventory part of the
// settings tab, shared by the admin and owner panels.
function InventoryFields({ website, mutate, isAdmin }: Props) {
    const { handlerUserApiRequest } = useUser();
    const { addAlert } = useAlerts();
    const [saving, setSaving] = useState(false);
    const [department, setDepartment] = useState(website.department ?? '');
    const [businessOwner, setBusinessOwner] = useState(website.business_owner ?? '');
    const { data: departments } = useSWR(
        '/api/websites/departments/',
        handlerUserApiRequest<string[]>
    );

    const save = async (body: Partial<Website>) => {
        setSaving(true);
        try {
            const updated = await handlerUserApiRequest<Website>(`/api/websites/${website.id}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });
            await mutate(updated);
            addAlert('Inventory updated', 'success');
        } catch (error) {
            addAlert('Failed to update: ' + (error as Error).message, 'error');
        }
        setSaving(false);
    };

    const departmentOptions = (departments ?? [])
        .filter((name) => name.toLowerCase().includes(department.toLowerCase()))
        .map((name) => ({ value: name }));

    return (
        <fieldset className="min-w-0">
            <Legend>Inventory</Legend>
            <div className="space-y-3">
                <Field
                    id="lifecycle"
                    label="Lifecycle"
                    help="Retired websites are no longer scanned on schedule or included in digests."
                >
                    {isAdmin ? (
                        <Select<WebsiteLifecycle>
                            id="lifecycle"
                            style={{ width: '100%' }}
                            value={website.lifecycle_status}
                            options={options(LIFECYCLE_LABELS)}
                            disabled={saving}
                            onChange={(value) => save({ lifecycle_status: value })}
                        />
                    ) : (
                        <div id="lifecycle" className="text-sm text-gray-700">
                            {LIFECYCLE_LABELS[website.lifecycle_status]}
                            <span className="ml-2 text-xs text-gray-600">Set by a site admin.</span>
                        </div>
                    )}
                </Field>
                <Field
                    id="sunset-date"
                    label="Sunset date"
                    help={
                        website.past_sunset
                            ? 'This date has passed and the website is not retired yet.'
                            : 'When the website is due to be retired, if it is.'
                    }
                >
                    {isAdmin ? (
                        <Input
                            id="sunset-date"
                            type="date"
                            status={website.past_sunset ? 'warning' : undefined}
                            defaultValue={website.sunset_date ?? ''}
                            disabled={saving}
                            onBlur={(e) => {
                                if ((e.target.value || null) !== website.sunset_date)
                                    save({ sunset_date: e.target.value || null });
                            }}
                        />
                    ) : (
                        <div id="sunset-date" className="text-sm text-gray-700">
                            {website.sunset_date ?? 'None'}
                        </div>
                    )}
                </Field>
                <Field id="department" label="Department or unit">
                    <AutoComplete
                        id="department"
                        style={{ width: '100%' }}
                        value={department}
                        options={departmentOptions}
                        placeholder="e.g. Computer Science"
                        disabled={saving}
                        onChange={setDepartment}
                        onBlur={() => {
                            if ((department.trim() || null) !== website.department)
                                save({ department: department.trim() || null });
                        }}
                        onSelect={(value: string) => save({ department: value })}
                    />
                </Field>
                <Field
                    id="business-owner"
                    label="Business owner"
                    help="Who is accountable for the content; the admin above is who gets the emails."
                >
                    <Input
                        id="business-owner"
                        value={businessOwner}
                        maxLength={200}
                        placeholder="Name or email"
                        disabled={saving}
                        onChange={(e) => setBusinessOwner(e.target.value)}
                        onBlur={() => {
                            if ((businessOwner.trim() || null) !== website.business_owner)
                                save({ business_owner: businessOwner.trim() || null });
                        }}
                    />
                </Field>
                <Field id="audience" label="Audience">
                    <Select<WebsiteAudience>
                        id="audience"
                        allowClear
                        style={{ width: '100%' }}
                        placeholder="Who uses it"
                        value={website.audience ?? undefined}
                        options={options(AUDIENCE_LABELS)}
                        disabled={saving}
                        onChange={(value) => save({ audience: value ?? null })}
                    />
                </Field>
                <Field id="criticality" label="Criticality">
                    {isAdmin ? (
                        <Select<WebsiteCriticality>
                            id="criticality"
                            allowClear
                            style={{ width: '100%' }}
                            placeholder="How much it matters"
                            value={website.criticality ?? undefined}
                            options={options(CRITICALITY_LABELS)}
                            disabled={saving}
                            onChange={(value) => save({ criticality: value ?? null })}
                        />
                    ) : (
                        <div id="criticality" className="text-sm text-gray-700">
                            {website.criticality
                                ? CRITICALITY_LABELS[website.criticality]
                                : 'Not set'}
                        </div>
                    )}
                </Field>
            </div>
        </fieldset>
    );
}

export default InventoryFields;

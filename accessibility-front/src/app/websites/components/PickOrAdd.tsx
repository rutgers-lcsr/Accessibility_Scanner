'use client';
import { Select } from 'antd';
import { useState } from 'react';

export type PickOption = { value: string; label: string };

type Props = {
    id: string;
    value: string | null;
    options: PickOption[];
    placeholder?: string;
    disabled?: boolean;
    // What the extra option says for a value that is not in the list yet.
    addLabel: (typed: string) => string;
    onChange: (value: string | null) => void;
    // Called as the person types, for lists fetched per search (users).
    onSearch?: (typed: string) => void;
};

const key = (value: string) => value.split(/\s+/).filter(Boolean).join(' ').toLowerCase();

// Pick an existing value, or add a new one only when nothing matches: "computer science"
// offers "Computer Science" instead of creating a second spelling.
function PickOrAdd({
    id,
    value,
    options,
    placeholder,
    disabled,
    addLabel,
    onChange,
    onSearch,
}: Props) {
    const [typed, setTyped] = useState('');
    const tidy = typed.split(/\s+/).filter(Boolean).join(' ');
    const exists = !tidy || options.some((option) => key(option.value) === key(tidy));
    const shown = [
        ...(value && !options.some((option) => option.value === value)
            ? [{ value, label: value }]
            : []),
        ...options,
        ...(exists ? [] : [{ value: tidy, label: addLabel(tidy) }]),
    ];

    return (
        <Select<string>
            id={id}
            showSearch
            allowClear
            style={{ width: '100%' }}
            placeholder={placeholder}
            disabled={disabled}
            value={value ?? undefined}
            options={shown}
            optionFilterProp="label"
            onSearch={(text) => {
                setTyped(text);
                onSearch?.(text);
            }}
            onChange={(next) => {
                setTyped('');
                onChange(next ?? null);
            }}
            notFoundContent={null}
        />
    );
}

export default PickOrAdd;

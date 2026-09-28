'use client';
import { LinkStatus } from '@/lib/types/link';
import {
    CheckCircleOutlined,
    CloseCircleOutlined,
    LockOutlined,
    MinusCircleOutlined,
    SyncOutlined,
    WarningOutlined,
} from '@ant-design/icons';
import { Tag, Tooltip } from 'antd';
import React from 'react';

// A link check result as icon + label (never colour alone), with the HTTP code and the
// error in a tooltip. Shared by the website Links tab and the page report.
export function LinkStatusTag({ status, code, error }: { status: LinkStatus; code: number | null; error: string | null }) {
    const meta: Record<LinkStatus, { label: string; color?: string; icon: React.ReactNode }> = {
        ok: { label: 'Working', color: 'green', icon: <CheckCircleOutlined /> },
        broken: { label: 'Broken', color: 'red', icon: <CloseCircleOutlined /> },
        error: { label: 'Error', color: 'orange', icon: <WarningOutlined /> },
        blocked: { label: 'Blocked', color: 'gold', icon: <LockOutlined /> },
        pending: { label: 'Not checked yet', icon: <SyncOutlined /> },
        skipped: { label: 'Skipped', icon: <MinusCircleOutlined /> },
    };
    const m = meta[status] ?? { label: status, icon: <MinusCircleOutlined /> };
    const tag = (
        <Tag color={m.color} icon={m.icon}>
            {m.label}
            {code !== null && ` (${code})`}
        </Tag>
    );
    return error ? <Tooltip title={error}>{tag}</Tooltip> : tag;
}

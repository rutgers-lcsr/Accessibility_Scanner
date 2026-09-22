'use client';
import { Impact } from '@/lib/types/dashboard';
import {
    AlertOutlined,
    ExclamationCircleOutlined,
    InfoCircleOutlined,
    WarningOutlined,
} from '@ant-design/icons';
import { Tag } from 'antd';
import { ReactNode } from 'react';

export type ImpactMeta = {
    key: Impact;
    label: string;
    tag: string;
    icon: ReactNode;
    text: string;
    bg: string;
    description: string;
};

// Severity presentation shared by the dashboard, the report pages and the violation
// cards: icon + label + colour, never colour alone. Most severe first.
export const IMPACTS: ImpactMeta[] = [
    {
        key: 'critical',
        label: 'Critical',
        tag: 'red',
        icon: <ExclamationCircleOutlined />,
        text: 'text-red-700',
        bg: 'bg-red-50',
        description:
            'Major barriers that prevent access for many users. Immediate attention required.',
    },
    {
        key: 'serious',
        label: 'Serious',
        tag: 'volcano',
        icon: <AlertOutlined />,
        text: 'text-red-700',
        bg: 'bg-red-100',
        description:
            'Significant issues that can make content difficult to use. Should be fixed promptly.',
    },
    {
        key: 'moderate',
        label: 'Moderate',
        tag: 'orange',
        icon: <WarningOutlined />,
        text: 'text-orange-700',
        bg: 'bg-orange-50',
        description: 'Problems that may inconvenience some users but do not block access.',
    },
    {
        key: 'minor',
        label: 'Minor',
        tag: 'gold',
        icon: <InfoCircleOutlined />,
        text: 'text-yellow-700',
        bg: 'bg-yellow-50',
        description: 'Low-impact issues that may affect usability in specific cases.',
    },
];

export const IMPACT_ORDER: Record<Impact, number> = {
    critical: 0,
    serious: 1,
    moderate: 2,
    minor: 3,
};

/** Sort rank: 0 for critical, larger for milder; unknown impacts sort last. */
export function impactRank(impact?: Impact | null): number {
    return impact ? IMPACT_ORDER[impact] : IMPACTS.length;
}

export function ImpactTag({ impact }: { impact?: Impact | null }) {
    const meta = IMPACTS.find((i) => i.key === impact);
    if (!meta) return <Tag>Unknown</Tag>;
    return (
        <Tag color={meta.tag} icon={meta.icon}>
            {meta.label}
        </Tag>
    );
}

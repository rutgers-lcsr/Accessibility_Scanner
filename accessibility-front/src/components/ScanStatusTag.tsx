'use client';
import { ScanStatus } from '@/lib/types/dashboard';
import {
    CheckCircleOutlined,
    CloseCircleOutlined,
    MinusCircleOutlined,
    WarningOutlined,
} from '@ant-design/icons';
import { Tag } from 'antd';

// How a website's last scan ended, as shown in the dashboard and owners tables.
function ScanStatusTag({
    status,
    lastScanned,
    stale = false,
}: {
    status: ScanStatus;
    lastScanned: string | null;
    // last scanned over 30 days ago: the scan ran fine, but its results may be out of date
    stale?: boolean;
}) {
    if (status === 'completed' && stale) {
        return (
            <Tag color="gold" icon={<WarningOutlined />}>
                Stale
            </Tag>
        );
    }
    if (status === 'completed') {
        return (
            <Tag color="green" icon={<CheckCircleOutlined />}>
                OK
            </Tag>
        );
    }
    if (status === 'failed') {
        return (
            <Tag color="red" icon={<CloseCircleOutlined />}>
                Failed
            </Tag>
        );
    }
    if (status === 'unreachable') {
        return (
            <Tag color="orange" icon={<WarningOutlined />}>
                Unreachable
            </Tag>
        );
    }
    return <Tag icon={<MinusCircleOutlined />}>{lastScanned ? 'Unknown' : 'Never scanned'}</Tag>;
}

export default ScanStatusTag;

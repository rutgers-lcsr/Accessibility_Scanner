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
}: {
    status: ScanStatus;
    lastScanned: string | null;
}) {
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

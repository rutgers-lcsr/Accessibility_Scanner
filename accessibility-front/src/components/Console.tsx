'use client';
import { useAlerts } from '@/providers/Alerts';
import { CopyOutlined } from '@ant-design/icons';
import '@ant-design/v5-patch-for-react-19';
import { Button, Tooltip } from 'antd';
import React from 'react';

type Props = {
    label: string;
    command: string;
};

const Console: React.FC<Props> = ({ label, command }) => {
    const { addAlert } = useAlerts();

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(command);
            addAlert(`Copied to clipboard`, 'success');
        } catch (err: unknown) {
            addAlert('Failed to copy to clipboard', 'error');
            console.error('Failed to copy command:', err);
        }
    };

    return (
        <div className="flex items-center rounded-md bg-gray-100 p-4" aria-label={label}>
            <span style={{ flex: 1 }}>{command}</span>
            <div className="ml-2">
                <Tooltip title="Copy">
                    <Button
                        icon={<CopyOutlined />}
                        onClick={handleCopy}
                        aria-label={`Copy ${label}`}
                    />
                </Tooltip>
            </div>
        </div>
    );
};

export default Console;

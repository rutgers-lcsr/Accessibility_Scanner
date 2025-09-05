'use client';
import { useAlerts } from '@/providers/Alerts';
import { CopyOutlined } from '@ant-design/icons';
import '@ant-design/v5-patch-for-react-19';
import { Button, Tooltip } from 'antd';
import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
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

    const markdown = `\`\`\`javascript\n${command}\n\`\`\``;

    return (
        <div className="flex items-center rounded-md bg-gray-100 p-4" aria-label={label}>
            <div className="flex-1 overflow-x-auto">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdown}</ReactMarkdown>
            </div>
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

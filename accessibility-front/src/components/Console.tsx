'use client';
import { useAlerts } from '@/providers/Alerts';
import '@/styles/console.css';
import { CopyOutlined } from '@ant-design/icons';
import '@ant-design/v5-patch-for-react-19';
import { Button, Tooltip } from 'antd';
import 'highlight.js/styles/github.css';
import React from 'react';
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import remarkGfm from 'remark-gfm';
type Props = {
    id?: string;
    label: string;
    command: string;
    mini?: boolean;
};

const Console: React.FC<Props> = ({ id, label, command, mini }) => {
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

    if (mini) {
        return (
            <Tooltip title="Copy">
                <Button icon={<CopyOutlined />} onClick={handleCopy} aria-label={`Copy ${label}`} />
            </Tooltip>
        );
    }

    const markdown = `\`\`\`javascript\n${command.trim()}\n\`\`\``;

    return (
        <div
            className="flex items-center rounded-md bg-gray-100 p-2 pb-2 relative "
            aria-label={label}
            id={id}
        >
            <div className="flex-1 h-fit w-full shadow-sm">
                <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
                    {markdown}
                </ReactMarkdown>
            </div>
            <div className="right-1 top-1 p-2 absolute">
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

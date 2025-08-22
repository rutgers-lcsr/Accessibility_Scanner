import React from "react";
import { Button, Tooltip, Typography, message } from "antd";
import { CopyOutlined } from "@ant-design/icons";


type Props = {
    label: string;
    command: string;
};

const Console: React.FC<Props> = ({ label, command }) => {
    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(command);
            message.success('Copied to clipboard!');
        } catch (err: unknown) {
            message.error('Failed to copy command');
            console.error("Failed to copy command:", err);
        }
    };

    return (
        <div
            className="bg-gray-100 p-4 rounded-md flex items-center"
            aria-label={label}
        >
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

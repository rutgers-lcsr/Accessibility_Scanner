import React from "react";
import { Button, Tooltip, Typography } from "antd";
import { CopyOutlined } from "@ant-design/icons";


type Props = {
    command: string;
};

const Console: React.FC<Props> = ({ command }) => {

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(command);
        } catch (err) {
        }
    };

    return (
        <div
            className="bg-[#222] text-[#0f0] font-mono p-4 rounded-lg h-[250px] overflow-y-auto shadow-md"
            aria-label="Fake console output"
        >
            <div className="mb-4 flex items-center">
                <Tooltip title="Click to copy command">
                    <Typography.Text
                        code
                        className="bg-[#333] px-4 py-2 rounded mr-2 select-all text-[#0f0]"
                    >
                        {command}
                    </Typography.Text>
                </Tooltip>
                <Button
                    icon={<CopyOutlined />}
                    onClick={handleCopy}
                    type="primary"
                    size="small"
                    className="!bg-[#444] !border-none !text-[#0f0] font-mono"
                    aria-label="Copy command"
                >
                    Copy
                </Button>
            </div>
        </div>
    );
};

export default Console;

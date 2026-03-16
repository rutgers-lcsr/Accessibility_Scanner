'use client';
import { AxeResult, WebsiteAxeResult } from '@/lib/types/axe';
import { CopyOutlined, RobotOutlined } from '@ant-design/icons';
import { Button, Modal, Tooltip, message } from 'antd';
import { useRef, useState } from 'react';

type Props = {
    violations: (AxeResult | WebsiteAxeResult)[];
    url?: string;
};

function isWebsiteResult(result: AxeResult | WebsiteAxeResult): result is WebsiteAxeResult {
    return (result as WebsiteAxeResult).reports !== undefined;
}

function buildPrompt(violations: (AxeResult | WebsiteAxeResult)[], url?: string): string {
    const lines: string[] = [];

    lines.push('# Accessibility Violations Report');
    if (url) {
        lines.push(`**URL:** ${url}`);
    }
    lines.push(`**Total Issues:** ${violations.length}`);
    lines.push('');
    lines.push(
        'Please fix the following accessibility violations. Each issue includes the rule ID, severity, description, and the affected HTML elements or pages.'
    );
    lines.push('');

    violations.forEach((v, i) => {
        lines.push(`## ${i + 1}. ${v.id} [${v.impact ?? 'unknown'}]`);
        lines.push(`- **Description:** ${v.description}`);
        lines.push(`- **Help:** ${v.help}`);
        lines.push(`- **Reference:** ${v.helpUrl}`);

        if (isWebsiteResult(v) && v.reports?.length) {
            lines.push(`- **Affected pages (${v.reports.length}):**`);
            v.reports.forEach((r) => {
                lines.push(`  - ${r.url}`);
            });
        }

        if (v.nodes?.length) {
            lines.push(`- **Affected elements (${v.nodes.length}):**`);
            v.nodes.forEach((node) => {
                lines.push(`  - Selector: \`${node.target.join(', ')}\``);
                lines.push(`    HTML: \`${node.html}\``);
                if (node.failureSummary) {
                    lines.push(`    Failure: ${node.failureSummary}`);
                }
            });
        }

        lines.push('');
    });

    return lines.join('\n');
}

function GenerateAIPromptButton({ violations, url }: Props) {
    const [open, setOpen] = useState(false);
    const preRef = useRef<HTMLPreElement>(null);

    if (!violations || violations.length === 0) return null;

    const prompt = open ? buildPrompt(violations, url) : '';

    const handleCopy = async () => {
        const text = buildPrompt(violations, url);
        try {
            await navigator.clipboard.writeText(text);
            message.success('Prompt copied to clipboard');
        } catch {
            message.error('Failed to copy to clipboard');
        }
    };

    return (
        <>
            <Tooltip title="Generate an AI agent prompt with all accessibility issues">
                <Button icon={<RobotOutlined />} onClick={() => setOpen(true)}>
                    AI Fix Prompt
                </Button>
            </Tooltip>
            <Modal
                title="AI Agent Prompt"
                open={open}
                onCancel={() => setOpen(false)}
                width={800}
                footer={[
                    <Button key="close" onClick={() => setOpen(false)}>
                        Close
                    </Button>,
                    <Button key="copy" type="primary" icon={<CopyOutlined />} onClick={handleCopy}>
                        Copy to Clipboard
                    </Button>,
                ]}
            >
                <p className="mb-2 text-sm text-gray-500">
                    Copy this prompt and paste it into your AI coding agent to fix all listed
                    accessibility issues.
                </p>
                <pre
                    ref={preRef}
                    className="max-h-[500px] overflow-auto rounded bg-gray-100 p-4 text-xs whitespace-pre-wrap"
                >
                    {prompt}
                </pre>
            </Modal>
        </>
    );
}

export default GenerateAIPromptButton;

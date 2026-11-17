'use client';
import { AxeResult, WebsiteAxeResult } from '@/lib/types/axe';
import { CopyOutlined, RobotOutlined } from '@ant-design/icons';
import { Button, Modal, Tooltip, message } from 'antd';
import { useState } from 'react';

type Props = {
    violations: (AxeResult | WebsiteAxeResult)[];
    url?: string;
};

function isWebsiteResult(result: AxeResult | WebsiteAxeResult): result is WebsiteAxeResult {
    return (result as WebsiteAxeResult).reports !== undefined;
}

function elementCount(v: AxeResult | WebsiteAxeResult): number {
    return isWebsiteResult(v) && v.reports?.length
        ? v.reports.reduce((sum, r) => sum + (r.node_count ?? 0), 0)
        : (v.nodes?.length ?? 0);
}

function buildPrompt(violations: (AxeResult | WebsiteAxeResult)[], url?: string): string {
    const lines: string[] = [];

    lines.push('# Accessibility Violations Report');
    if (url) {
        lines.push(`**URL:** ${url}`);
    }
    // Elements, the unit the rest of the app counts in; a website rule carries its
    // element count per page, a page report the elements themselves.
    const elements = violations.reduce((sum, v) => sum + elementCount(v), 0);
    lines.push(
        `**Failing elements:** ${elements} across ${violations.length} rule${violations.length === 1 ? '' : 's'}`
    );
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

        const website = isWebsiteResult(v) && !!v.reports?.length;
        if (website) {
            lines.push(`- **Affected pages (${v.reports.length}), most elements first:**`);
            [...v.reports]
                .sort((a, b) => (b.node_count ?? 0) - (a.node_count ?? 0))
                .forEach((r) => {
                    const n = r.node_count;
                    lines.push(`  - ${r.url}${n ? ` (${n} element${n === 1 ? '' : 's'})` : ''}`);
                });
        }

        if (v.nodes?.length) {
            // On the website view only the first page's elements come along: say so, so
            // an agent does not take the sample for the whole list.
            lines.push(
                website
                    ? `- **Example elements from the first affected page (${v.nodes.length} of ${elementCount(v)}); open each page above for all of them:**`
                    : `- **Affected elements (${v.nodes.length}), all of them:**`
            );
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
                <pre className="max-h-[500px] overflow-auto rounded bg-gray-100 p-4 text-xs whitespace-pre-wrap">
                    {prompt}
                </pre>
            </Modal>
        </>
    );
}

export default GenerateAIPromptButton;

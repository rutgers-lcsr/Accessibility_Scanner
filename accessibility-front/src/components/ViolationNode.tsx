'use client';
import { AxeNode } from '@/lib/types/axe';
import { Button } from 'antd';

// Fired on window when the user asks to see an element in the page preview; PageIframe listens.
export const PREVIEW_FOCUS_EVENT = 'a11y:preview-focus';

/** The selector the highlight script uses for this node (same join as style_generator.py). */
export function nodeSelector(node: AxeNode): string {
    return (node.target ?? []).join(', ');
}

type Props = {
    node: AxeNode;
    previewEnabled?: boolean;
};

// One failing element: selector, its HTML (as text, never rendered) and axe's fix summary.
function ViolationNode({ node, previewEnabled = false }: Props) {
    const selector = nodeSelector(node);
    const focusInPreview = () =>
        window.dispatchEvent(new CustomEvent(PREVIEW_FOCUS_EVENT, { detail: { selector } }));

    return (
        <li className="mb-3 rounded border border-gray-200 bg-gray-50 p-2 text-xs text-gray-700">
            <div className="flex items-start justify-between gap-2">
                <code className="break-all">{selector || '(no selector)'}</code>
                {previewEnabled && selector && (
                    <Button size="small" onClick={focusInPreview}>
                        Show in preview
                    </Button>
                )}
            </div>
            {node.html && (
                <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap break-all rounded bg-white p-2">
                    <code>{node.html}</code>
                </pre>
            )}
            {node.failureSummary && (
                <div className="mt-2 whitespace-pre-wrap text-gray-600">{node.failureSummary}</div>
            )}
        </li>
    );
}

export default ViolationNode;

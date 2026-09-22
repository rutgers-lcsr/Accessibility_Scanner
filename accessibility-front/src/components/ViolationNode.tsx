'use client';
import FindingStatusControl from '@/components/FindingStatusControl';
import { AxeNode } from '@/lib/types/axe';
import { Finding } from '@/lib/types/finding';
import { Button } from 'antd';

// Fired on window when the user asks to see an element in the page preview; PageIframe listens.
export const PREVIEW_FOCUS_EVENT = 'a11y:preview-focus';

/** The selector the highlight script uses for this node (same join as style_generator.py). */
export function nodeSelector(node: AxeNode): string {
    return (node.target ?? []).join(', ');
}

/** The selector findings are keyed by (services.findings.normalise_selector). */
export function findingSelector(node: AxeNode): string {
    return (node.target ?? []).flat().join(' >>> ');
}

/** Lookup key for a finding: one element can fail several rules. */
export function findingKey(ruleId: string, selector: string | null): string {
    return `${ruleId}\u0000${selector ?? ''}`;
}

type Props = {
    node: AxeNode;
    previewEnabled?: boolean;
    // The finding tracked for this element, when the report is the page's latest.
    finding?: Finding;
    canEdit?: boolean;
    onFindingChanged?: (finding: Finding) => void;
};

// One failing element: selector, its HTML (as text, never rendered), axe's fix summary,
// and the verdict on it when findings are tracked.
function ViolationNode({
    node,
    previewEnabled = false,
    finding,
    canEdit = false,
    onFindingChanged,
}: Props) {
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
            {finding && (
                <div className="mt-2">
                    <FindingStatusControl
                        finding={finding}
                        canEdit={canEdit}
                        onChanged={onFindingChanged}
                    />
                </div>
            )}
        </li>
    );
}

export default ViolationNode;

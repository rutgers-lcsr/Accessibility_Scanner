'use client';
import FindingStatusControl from '@/components/FindingStatusControl';
import { AxeNode } from '@/lib/types/axe';
import { Finding } from '@/lib/types/finding';
import { useAlerts } from '@/providers/Alerts';
import { CopyOutlined } from '@ant-design/icons';
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

    const summary = plainSummary(node.failureSummary);
    const text = visibleText(node.html);
    const { addAlert } = useAlerts();
    const copy = async (value: string, what: string) => {
        try {
            await navigator.clipboard.writeText(value);
            addAlert(`${what} copied`, 'success');
        } catch {
            addAlert(`Could not copy the ${what.toLowerCase()}`, 'error');
        }
    };

    return (
        <li className="mb-3 rounded border border-gray-200 bg-gray-50 p-3 text-sm text-gray-800">
            {/* What is wrong first, in words; then the words on the page, so a non-coder can
                find it; the selector and HTML are for finding it in code. */}
            {summary && <div className="mb-2 whitespace-pre-wrap">{summary}</div>}
            {text && (
                <p className="text-gray-900" style={{ margin: '0 0 8px' }}>
                    On the page it reads: <q className="font-medium">{text}</q>
                </p>
            )}
            <div className="flex flex-wrap items-start gap-2 text-xs text-gray-700">
                <code className="min-w-0 flex-1 basis-48 break-all">
                    {selector || '(no selector)'}
                </code>
                <span className="flex flex-wrap gap-2">
                    {selector && (
                        <Button
                            size="small"
                            icon={<CopyOutlined />}
                            onClick={() => copy(selector, 'Selector')}
                            aria-label={`Copy selector ${selector}`}
                        >
                            Copy
                        </Button>
                    )}
                    {previewEnabled && selector && (
                        <Button
                            size="small"
                            onClick={focusInPreview}
                            aria-label={`Show ${text ? `“${text}”` : selector} in the preview`}
                        >
                            Show in preview
                        </Button>
                    )}
                </span>
            </div>
            {node.html && (
                // Focusable: a keyboard user can scroll a long snippet.
                <section
                    tabIndex={0}
                    aria-label={`HTML of ${selector || 'the element'}`}
                    className="mt-2 max-h-40 overflow-auto rounded bg-white p-2"
                >
                    <pre className="whitespace-pre-wrap break-all text-xs" style={{ margin: 0 }}>
                        <code>{node.html}</code>
                    </pre>
                </section>
            )}
            {finding && (
                <div className="mt-2">
                    <FindingStatusControl
                        finding={finding}
                        elementName={text ? `“${text}”` : selector}
                        canEdit={canEdit}
                        onChanged={onFindingChanged}
                    />
                </div>
            )}
        </li>
    );
}

// The words an element shows, from axe's (possibly truncated) HTML: tags dropped,
// entities for quotes and ampersands decoded, whitespace collapsed. Empty when the
// snippet holds no text (an image, an empty button, an opening tag only).
function visibleText(html?: string): string {
    if (!html) return '';
    const text = html
        .replace(/<[^>]*>?/g, ' ')
        .replace(/&nbsp;/g, ' ')
        .replace(/&amp;/g, '&')
        .replace(/&quot;/g, '"')
        .replace(/&#39;/g, "'")
        .replace(/&lt;/g, '<')
        .replace(/&gt;/g, '>')
        .replace(/\s+/g, ' ')
        .trim();
    return text.length > 120 ? `${text.slice(0, 117)}…` : text;
}

// axe's summary opens each group with "Fix any of the following:" / "Fix all of the
// following:"; say what that means.
function plainSummary(summary?: string): string {
    if (!summary) return '';
    // One line under a heading is a diagnosis, not a list of choices: say "What failed".
    // Stored summaries are sometimes flattened onto one line ("Fix any of the following:
    // Element has …"): one remedy either way.
    const single = summary.match(/^Fix (?:any|all) of the following:\s*([^\n]+)$/);
    if (single) return `What failed: ${single[1].trim()}`;
    return summary
        .replace(/Fix any of the following:\n(\s*[^\n]+)\s*$/g, 'What failed:\n$1')
        .replace(/Fix all of the following:\n(\s*[^\n]+)\s*$/g, 'What failed:\n$1')
        .replace(/Fix any of the following:/g, 'Any one of these fixes it:')
        .replace(/Fix all of the following:/g, 'All of these need fixing:')
        .trim();
}

export default ViolationNode;

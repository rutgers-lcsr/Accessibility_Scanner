'use client';
import PageLoading from '@/components/PageLoading';
import { fetcherApi } from '@/lib/api';
import { isCodeHighlight, parseContrast, plainContrastFix } from '@/lib/contrast';
import { PublicUser } from '@/lib/types/user';
import { useAlerts } from '@/providers/Alerts';
import { useUser } from '@/providers/User';
import { CopyOutlined, DownloadOutlined } from '@ant-design/icons';
import { Button, Collapse, Drawer, Space, Tag } from 'antd';
import StatusDialog from '@/components/StatusDialog';
import { STATUS_LABELS } from '@/lib/findings';
import { FindingStatus } from '@/lib/types/finding';
import { useState } from 'react';
import useSWR from 'swr';

type Element = {
    id: number;
    url: string;
    report_id: number | null;
    selector: string | null;
    html: string | null;
    failure_summary: string | null;
    status: string;
    note: string | null;
};
type Group = {
    key: string;
    label: string;
    rule_id: string;
    impact: string | null;
    help: string | null;
    count: number;
    pages: number;
    elements: Element[];
};
type Elements = { count: number; groups: Group[] };

type Props = {
    websiteId: number;
    ruleId: string;
    title: string;
    user: PublicUser | null;
    open: boolean;
    onClose: () => void;
    // Called once the drawer has closed, to put focus back where it was.
    afterClose?: () => void;
    // May set statuses (the website's admin, members, site admins).
    canEdit?: boolean;
    // After a group's status changed: refresh what showed the counts.
    onChanged?: () => void;
};

const plural = (n: number, noun: string) => `${n} ${noun}${n === 1 ? '' : 's'}`;
const shortUrl = (url: string) => url.replace(/^https?:\/\//, '');

// The words an element shows, from its (possibly truncated) HTML.
function visibleText(html: string | null): string {
    const text = (html ?? '')
        .replace(/<[^>]*>?/g, ' ')
        .replace(/\s+/g, ' ')
        .trim();
    return text.length > 80 ? `${text.slice(0, 77)}…` : text;
}

// The fix sentence for a whole group, only when it holds for every member: elements of
// one markup can differ in size (and so in the ratio they need).
function groupFix(group: Group): string | null {
    const first = group.elements[0];
    const failures = group.elements.map((e) => parseContrast(e.failure_summary));
    if (!failures[0] || failures.some((f) => !f || f.expected !== failures[0]?.expected))
        return null;
    return plainContrastFix(first.failure_summary, first);
}

// An agent prompt with every element, grouped, with the HTML of each group's first element.
function prompt(title: string, data: Elements): string {
    const lines = [
        `# ${title}`,
        '',
        `**Failing elements:** ${data.count}, in ${plural(data.groups.length, 'group')}. Elements in one group have the same tag, classes and colours; they often share one source (a template, a stylesheet rule, a code-highlighting theme). Find that source and fix it once where you can, then check each element.`,
        '',
    ];
    data.groups.forEach((group, i) => {
        lines.push(
            `## ${i + 1}. ${group.label} (${plural(group.count, 'element')} on ${plural(group.pages, 'page')})`
        );
        const fix = groupFix(group);
        if (fix) lines.push(fix);
        if (group.elements[0]?.html) lines.push('', '```html', group.elements[0].html, '```');
        group.elements.forEach((e) => lines.push(`- ${e.url} \`${e.selector ?? ''}\``));
        lines.push('');
    });
    return lines.join('\n');
}

// Every current failing element of one rule across the website, grouped by the markup
// it shares, with downloads. A drawer: it takes focus, closes on Escape, and the caller
// puts focus back on the button that opened it.
export default function RuleElements({
    websiteId,
    ruleId,
    title,
    user,
    open,
    onClose,
    afterClose,
    canEdit = false,
    onChanged,
}: Props) {
    // The group whose status is being set.
    const [statusFor, setStatusFor] = useState<Group | null>(null);
    const { handlerUserApiRequest } = useUser();
    const { addAlert } = useAlerts();
    const base = `/api/websites/${websiteId}/elements/?rule=${encodeURIComponent(ruleId)}`;
    const { data, error, mutate, isValidating } = useSWR(
        open ? base : null,
        user ? handlerUserApiRequest<Elements> : fetcherApi<Elements>
    );
    const copy = async (value: string, what: string) => {
        try {
            await navigator.clipboard.writeText(value);
            addAlert(`${what} copied`, 'success');
        } catch {
            addAlert(
                `Could not copy the ${what.toLowerCase()}; select it and copy by hand`,
                'error'
            );
        }
    };
    const setGroupStatus = async (group: Group, status: FindingStatus, note?: string) => {
        try {
            const result = await handlerUserApiRequest<{ updated: number }>(
                `/api/websites/${websiteId}/findings/bulk-ids/`,
                {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        ids: group.elements.map((e) => e.id),
                        status,
                        ...(note ? { note } : {}),
                    }),
                }
            );
            addAlert(
                `${plural(result.updated, 'element')} marked ${STATUS_LABELS[status].toLowerCase()}`,
                'success'
            );
            await mutate();
            onChanged?.();
        } catch (error) {
            addAlert('Could not update the elements: ' + (error as Error).message, 'error');
        }
    };
    const fileBase = `elements-${websiteId}-${ruleId.replace(/[^a-z0-9-]/gi, '')}`;

    return (
        <Drawer
            open={open}
            onClose={onClose}
            afterOpenChange={(isOpen) => {
                if (!isOpen) afterClose?.();
            }}
            title={
                <span className="block text-base leading-snug">
                    Every element <span className="font-normal text-gray-700">· {title}</span>
                </span>
            }
            size="large"
        >
            {error ? (
                <div>
                    <p style={{ margin: '0 0 12px' }}>Could not load the elements.</p>
                    <Button onClick={() => mutate()} loading={isValidating}>
                        Try again
                    </Button>
                </div>
            ) : !data ? (
                <PageLoading />
            ) : (
                <>
                    <Space wrap style={{ marginBottom: 16 }}>
                        <Button icon={<DownloadOutlined />} href={`${base}&format=csv`}>
                            Download CSV
                        </Button>
                        <Button
                            icon={<DownloadOutlined />}
                            href={base}
                            download={`${fileBase}.json`}
                        >
                            Download JSON
                        </Button>
                        <Button
                            icon={<CopyOutlined />}
                            onClick={() => copy(prompt(title, data), 'AI prompt')}
                        >
                            Copy AI prompt
                        </Button>
                    </Space>
                    <p style={{ margin: '0 0 16px' }}>
                        {plural(data.count, 'element')} in {plural(data.groups.length, 'group')}.
                        Elements in one group have the same tag, classes
                        {data.groups.some((g) => g.label.includes(' on #')) && ' and colours'}. They
                        often share one source, such as a template, a stylesheet rule or a
                        code-highlighting theme, so look for it before fixing them one by one.
                    </p>
                    <Collapse
                        defaultActiveKey={
                            data.groups.length <= 3
                                ? data.groups.map((g) => g.key)
                                : [data.groups[0]?.key]
                        }
                        items={data.groups.map((group) => {
                            const fix = groupFix(group);
                            const code = group.elements.some((e) => isCodeHighlight(e));
                            const urls = new Set(group.elements.map((e) => e.url));
                            const onePage = urls.size === 1 ? group.elements[0] : null;
                            const colours = parseContrast(group.elements[0]?.failure_summary);
                            const selectors = group.elements
                                .map((e) => e.selector)
                                .filter(Boolean)
                                .join('\n');
                            return {
                                key: group.key,
                                label: (
                                    <span className="flex flex-wrap items-center gap-x-3 gap-y-1">
                                        {colours && (
                                            // The two colours, seen: hex codes alone mean nothing to most owners.
                                            <span
                                                aria-hidden="true"
                                                className="inline-flex overflow-hidden rounded border border-gray-300"
                                            >
                                                <span
                                                    className="h-4 w-4"
                                                    style={{ background: colours.foreground }}
                                                />
                                                <span
                                                    className="h-4 w-4"
                                                    style={{ background: colours.background }}
                                                />
                                            </span>
                                        )}
                                        {code && (
                                            <span className="font-medium">
                                                Code-highlighting colours
                                            </span>
                                        )}
                                        <code className="text-sm">{group.label}</code>
                                        <span className="text-sm text-gray-700">
                                            {plural(group.count, 'element')} on{' '}
                                            {plural(group.pages, 'page')}
                                        </span>
                                    </span>
                                ),
                                children: (
                                    <>
                                        {fix ? (
                                            <p
                                                className="font-medium"
                                                style={{ margin: '0 0 8px' }}
                                            >
                                                {fix}
                                            </p>
                                        ) : (
                                            code && (
                                                <p
                                                    className="font-medium"
                                                    style={{ margin: '0 0 8px' }}
                                                >
                                                    These are code-highlighting colours: choose a
                                                    higher-contrast highlighting theme rather than
                                                    recolouring words.
                                                </p>
                                            )
                                        )}
                                        <Space wrap style={{ marginBottom: 8 }}>
                                            {onePage && (
                                                <span className="text-sm">
                                                    All on{' '}
                                                    {onePage.report_id ? (
                                                        <a
                                                            href={`/reports/${onePage.report_id}?rule=${encodeURIComponent(ruleId)}#violation-${encodeURIComponent(ruleId)}`}
                                                        >
                                                            {shortUrl(onePage.url)}
                                                        </a>
                                                    ) : (
                                                        shortUrl(onePage.url)
                                                    )}
                                                </span>
                                            )}
                                            <Button
                                                size="small"
                                                icon={<CopyOutlined />}
                                                onClick={() => copy(selectors, 'Selectors')}
                                            >
                                                Copy all {group.count} selectors
                                            </Button>
                                            {canEdit && (
                                                <Button
                                                    size="small"
                                                    aria-haspopup="dialog"
                                                    onClick={() => setStatusFor(group)}
                                                >
                                                    Set status for these {group.count}…
                                                </Button>
                                            )}
                                        </Space>
                                        <ul className="m-0 list-none p-0">
                                            {group.elements.map((element) => {
                                                const text = visibleText(element.html);
                                                const at = element.report_id
                                                    ? `/reports/${element.report_id}?rule=${encodeURIComponent(ruleId)}#violation-${encodeURIComponent(ruleId)}`
                                                    : null;
                                                return (
                                                    <li
                                                        key={element.id}
                                                        className="border-b border-gray-100 py-2 last:border-0"
                                                    >
                                                        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                                                            {text && (
                                                                <q className="font-medium">
                                                                    {text}
                                                                </q>
                                                            )}
                                                            {!onePage &&
                                                                (at ? (
                                                                    <a
                                                                        href={at}
                                                                        className="text-sm"
                                                                    >
                                                                        {shortUrl(element.url)}
                                                                    </a>
                                                                ) : (
                                                                    <span className="text-sm">
                                                                        {shortUrl(element.url)}
                                                                    </span>
                                                                ))}
                                                            {element.status !== 'open' && (
                                                                <Tag>
                                                                    {element.status.replace(
                                                                        '_',
                                                                        ' '
                                                                    )}
                                                                </Tag>
                                                            )}
                                                        </div>
                                                        <div className="mt-1 flex items-start gap-2">
                                                            {/* Wraps at the selector's steps, not mid-word. */}
                                                            <code className="min-w-0 flex-1 text-xs [overflow-wrap:anywhere]">
                                                                {(element.selector ?? '')
                                                                    .split(' > ')
                                                                    .join(' >​ ')}
                                                            </code>
                                                            {element.selector && (
                                                                <Button
                                                                    size="small"
                                                                    icon={<CopyOutlined />}
                                                                    aria-label={`Copy selector ${element.selector}`}
                                                                    onClick={() =>
                                                                        copy(
                                                                            element.selector ?? '',
                                                                            'Selector'
                                                                        )
                                                                    }
                                                                />
                                                            )}
                                                        </div>
                                                        {element.html && (
                                                            <details className="mt-1 text-xs">
                                                                <summary className="cursor-pointer text-gray-700">
                                                                    HTML
                                                                </summary>
                                                                <pre
                                                                    className="mt-1 whitespace-pre-wrap rounded bg-gray-50 p-2"
                                                                    style={{
                                                                        margin: 0,
                                                                        overflowWrap: 'anywhere',
                                                                    }}
                                                                >
                                                                    {element.html}
                                                                </pre>
                                                            </details>
                                                        )}
                                                    </li>
                                                );
                                            })}
                                        </ul>
                                    </>
                                ),
                            };
                        })}
                    />
                    {statusFor && (
                        <StatusDialog
                            open
                            count={statusFor.count}
                            title={`Status for these ${plural(statusFor.count, 'element')}`}
                            scope={`${statusFor.label}, on ${plural(statusFor.pages, 'page')}.`}
                            onCancel={() => setStatusFor(null)}
                            onConfirm={(status, note) => {
                                const group = statusFor;
                                setStatusFor(null);
                                setGroupStatus(group, status, note);
                            }}
                        />
                    )}
                </>
            )}
        </Drawer>
    );
}

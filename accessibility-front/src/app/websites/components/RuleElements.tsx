'use client';
import { fetcherApi } from '@/lib/api';
import { plainContrastFix } from '@/lib/contrast';
import { reportHref } from '@/lib/guides';
import { PublicUser } from '@/lib/types/user';
import { useAlerts } from '@/providers/Alerts';
import { useUser } from '@/providers/User';
import { CopyOutlined, DownloadOutlined } from '@ant-design/icons';
import { Button, Collapse, Drawer, Space, Tag } from 'antd';
import useSWR from 'swr';
import PageLoading from '@/components/PageLoading';

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
};

const plural = (n: number, noun: string) => `${n} ${noun}${n === 1 ? '' : 's'}`;
const shortUrl = (url: string) => url.replace(/^https?:\/\//, '');

// An agent prompt with every element, grouped, so one fix per group can be made at its
// source (a template, a stylesheet) rather than element by element.
function prompt(title: string, data: Elements): string {
    const lines = [
        `# ${title}`,
        '',
        `**Failing elements:** ${data.count}, in ${plural(data.groups.length, 'group')} of shared markup.`,
        '',
    ];
    lines.push(
        'Elements in one group share their markup (and colours), so they usually come from one template or stylesheet rule: fix it there once.',
        ''
    );
    data.groups.forEach((group, i) => {
        lines.push(
            `## ${i + 1}. ${group.label} (${plural(group.count, 'element')} on ${plural(group.pages, 'page')})`
        );
        const fix = plainContrastFix(group.elements[0]?.failure_summary);
        if (fix) lines.push(fix);
        group.elements.forEach((e) => lines.push(`- ${e.url} \`${e.selector ?? ''}\``));
        lines.push('');
    });
    return lines.join('\n');
}

// Every current failing element of one rule across the website, grouped by the markup
// it shares, with downloads. A drawer: it takes focus and gives it back when closed.
export default function RuleElements({ websiteId, ruleId, title, user, open, onClose }: Props) {
    const { handlerUserApiRequest } = useUser();
    const { addAlert } = useAlerts();
    const base = `/api/websites/${websiteId}/elements/?rule=${encodeURIComponent(ruleId)}`;
    const { data, error } = useSWR(
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

    return (
        <Drawer
            open={open}
            onClose={onClose}
            title={`Every element: ${title}`}
            size="large"
            extra={
                data && (
                    <Space wrap>
                        <Button icon={<DownloadOutlined />} href={`${base}&format=csv`}>
                            CSV
                        </Button>
                        <Button icon={<DownloadOutlined />} href={base} target="_blank">
                            JSON
                        </Button>
                        <Button
                            icon={<CopyOutlined />}
                            onClick={() => copy(prompt(title, data), 'AI prompt')}
                        >
                            AI prompt
                        </Button>
                    </Space>
                )
            }
        >
            {error ? (
                <p>Could not load the elements.</p>
            ) : !data ? (
                <PageLoading />
            ) : (
                <>
                    <p style={{ margin: '0 0 16px' }}>
                        {plural(data.count, 'element')} in {plural(data.groups.length, 'group')}.
                        Elements in one group share their markup
                        {data.groups.some((g) => g.label.includes(' on #')) && ' and colours'}, so
                        they usually come from one template or style: one change there fixes the
                        whole group.
                    </p>
                    <Collapse
                        defaultActiveKey={
                            data.groups.length <= 3
                                ? data.groups.map((g) => g.key)
                                : [data.groups[0]?.key]
                        }
                        items={data.groups.map((group) => {
                            const fix = plainContrastFix(group.elements[0]?.failure_summary);
                            return {
                                key: group.key,
                                label: (
                                    <span className="flex flex-wrap items-center gap-2">
                                        <code className="break-all">{group.label}</code>
                                        <Tag>{plural(group.count, 'element')}</Tag>
                                        <span className="text-sm text-gray-700">
                                            on {plural(group.pages, 'page')}
                                        </span>
                                    </span>
                                ),
                                children: (
                                    <>
                                        {fix && (
                                            <p
                                                className="font-medium"
                                                style={{ margin: '0 0 12px' }}
                                            >
                                                {fix}
                                            </p>
                                        )}
                                        <ul className="m-0 list-none p-0">
                                            {group.elements.map((element) => {
                                                const href = reportHref(element.report_id, ruleId);
                                                return (
                                                    <li
                                                        key={element.id}
                                                        className="flex flex-wrap items-center gap-2 border-b border-gray-100 py-2 last:border-0"
                                                    >
                                                        {href ? (
                                                            <a href={href} className="break-all">
                                                                {shortUrl(element.url)}
                                                            </a>
                                                        ) : (
                                                            <span className="break-all">
                                                                {shortUrl(element.url)}
                                                            </span>
                                                        )}
                                                        <code className="min-w-0 flex-1 basis-48 break-all text-xs">
                                                            {element.selector}
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
                                                            >
                                                                Copy
                                                            </Button>
                                                        )}
                                                        {element.status !== 'open' && (
                                                            <Tag>
                                                                {element.status.replace('_', ' ')}
                                                            </Tag>
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
                </>
            )}
        </Drawer>
    );
}

'use client';
import { RuleFindingsSummary } from '@/components/AuditAccessibilityItem';
import ViolationNode from '@/components/ViolationNode';
import { guideHref, reportHref, violationsHref } from '@/lib/guides';
import { ImpactTag } from '@/lib/impact';
import { FindingStatus, FixFirstPage, FixFirstRule, WebsiteFixFirst } from '@/lib/types/finding';
import { PlatformId } from '@/lib/types/guide';
import { Alert, Button, Card, Collapse, Progress, Space, Tag } from 'antd';
import { ReactNode, useEffect, useRef } from 'react';

type Props = {
    websiteId: number;
    data: WebsiteFixFirst;
    canEdit: boolean;
    // Pre-selects the platform tab of the guides (from the website's categories).
    platform: PlatformId | null;
    onBulkStatus?: (ruleId: string, status: FindingStatus) => Promise<void>;
    // Rendered at the end of every page row (the rescan action, once it exists).
    renderPageAction?: (page: FixFirstPage, rule: FixFirstRule) => ReactNode;
    // The rule to scroll to on arrival (?rule=), from an email.
    focusRule?: string | null;
};

const plural = (count: number, noun: string) => `${count} ${noun}${count === 1 ? '' : 's'}`;

// The website's open violations as a ranked to-do list: one fix in a template usually
// clears the same rule on every page that uses it, so rules are ordered by pages cleared.
function FixFirstList({
    websiteId,
    data,
    canEdit,
    platform,
    onBulkStatus,
    renderPageAction,
    focusRule,
}: Props) {
    const scrolled = useRef(false);
    useEffect(() => {
        if (!focusRule || scrolled.current) return;
        const card = document.getElementById(`fix-${focusRule}`);
        if (card) {
            scrolled.current = true;
            card.scrollIntoView({ block: 'start' });
        }
    }, [focusRule, data]);

    if (data.pages_audited === 0) {
        return (
            <Alert type="info" showIcon message="No page of this website has been scanned yet." />
        );
    }
    if (data.rules.length === 0) {
        return (
            <Alert
                type="success"
                showIcon
                message="No open violations on the audited pages."
                description={
                    data.suppressed_rules > 0
                        ? `${plural(data.suppressed_rules, 'rule')} fully marked false positive or accepted.`
                        : undefined
                }
            />
        );
    }

    const topThree = data.rules.slice(0, 3).reduce((sum, rule) => sum + rule.elements, 0);
    const topShare = data.open_total ? Math.round((100 * topThree) / data.open_total) : 0;

    return (
        <div>
            <p className="mb-4 text-gray-700">
                {data.pages_audited} of {plural(data.pages_total, 'page')} audited.{' '}
                <strong>{plural(data.open_total, 'open issue')}</strong> across{' '}
                {plural(data.rules.length, 'rule')}
                {data.rules.length > 3 && `; the first three account for ${topShare}% of them`}.
                {data.suppressed_rules > 0 &&
                    ` ${plural(data.suppressed_rules, 'rule')} fully marked false positive or accepted ${
                        data.suppressed_rules === 1 ? 'is' : 'are'
                    } not listed.`}
            </p>
            <ol className="m-0 list-none space-y-4 p-0">
                {data.rules.map((rule, index) => {
                    const example = rule.example;
                    const guide = rule.guide ? guideHref(rule.rule_id, platform) : null;
                    return (
                        <li key={rule.rule_id} id={`fix-${rule.rule_id}`}>
                            <Card
                                title={
                                    <div className="flex flex-wrap items-baseline gap-2">
                                        <h3 className="text-lg font-semibold" style={{ margin: 0 }}>
                                            {index + 1}. {rule.help ?? rule.rule_id}
                                        </h3>
                                        <span className="text-xs font-normal text-gray-500">
                                            {rule.rule_id}
                                        </span>
                                    </div>
                                }
                                extra={<ImpactTag impact={rule.impact} />}
                            >
                                <p className="mb-1 font-medium">
                                    Fixing this clears {plural(rule.elements, 'issue')} on{' '}
                                    {rule.pages_affected} of {plural(data.pages_audited, 'page')}
                                </p>
                                <Progress
                                    percent={rule.pages_cleared_percent}
                                    size="small"
                                    showInfo={false}
                                    aria-hidden
                                />
                                <RuleFindingsSummary
                                    ruleId={rule.rule_id}
                                    group={rule}
                                    canEdit={canEdit}
                                    onBulkStatus={onBulkStatus}
                                />
                                <Collapse
                                    className="mt-3"
                                    items={[
                                        {
                                            key: 'example',
                                            label: (
                                                <span className="font-medium">
                                                    Example element
                                                    <span className="ml-2 text-xs font-normal text-gray-500">
                                                        on {example.url}
                                                    </span>
                                                </span>
                                            ),
                                            children: (
                                                <ul className="m-0 list-none p-0">
                                                    <ViolationNode
                                                        node={{
                                                            target: [example.selector ?? ''],
                                                            html: example.html ?? '',
                                                            failureSummary:
                                                                example.failure_summary ??
                                                                undefined,
                                                            any: [],
                                                            all: [],
                                                            none: [],
                                                        }}
                                                    />
                                                </ul>
                                            ),
                                        },
                                        {
                                            key: 'pages',
                                            label: (
                                                <span className="font-medium">
                                                    Pages ({rule.pages_affected})
                                                </span>
                                            ),
                                            children: (
                                                <ul className="m-0 list-none p-0">
                                                    {rule.pages.map((page) => {
                                                        const href = reportHref(
                                                            page.report_id,
                                                            rule.rule_id
                                                        );
                                                        return (
                                                            <li
                                                                key={page.site_id}
                                                                className="flex flex-wrap items-center gap-2 border-b border-gray-100 py-1 last:border-0"
                                                            >
                                                                {href ? (
                                                                    <a
                                                                        href={href}
                                                                        className="break-all"
                                                                    >
                                                                        {page.url}
                                                                    </a>
                                                                ) : (
                                                                    <span className="break-all">
                                                                        {page.url}
                                                                    </span>
                                                                )}
                                                                <Tag>
                                                                    {plural(page.count, 'element')}
                                                                </Tag>
                                                                {renderPageAction?.(page, rule)}
                                                            </li>
                                                        );
                                                    })}
                                                </ul>
                                            ),
                                        },
                                    ]}
                                />
                                <Space className="mt-3" wrap>
                                    {guide ? (
                                        <Button type="primary" href={guide}>
                                            Fix guide
                                        </Button>
                                    ) : (
                                        rule.help_url && (
                                            <Button
                                                href={rule.help_url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                            >
                                                How to fix (Deque)
                                            </Button>
                                        )
                                    )}
                                    <Button href={violationsHref(websiteId, rule.rule_id)}>
                                        Details
                                    </Button>
                                </Space>
                            </Card>
                        </li>
                    );
                })}
            </ol>
        </div>
    );
}

export default FixFirstList;

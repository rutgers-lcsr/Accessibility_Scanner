'use client';
import AuditAccessibilityItem from '@/components/AuditAccessibilityItem';
import GenerateAIPromptButton from '@/components/GenerateAIPromptButton';
import { IMPACTS, impactRank } from '@/lib/impact';
import { AxeResult, WebsiteAxeResult } from '@/lib/types/axe';
import { Impact } from '@/lib/types/dashboard';
import { useUrlFilters } from '@/lib/urlFilters';
import { Button, Flex, Input, Select, Space } from 'antd';
import { useEffect, useRef } from 'react';

type Violation = AxeResult | WebsiteAxeResult;
type SortKey = 'impact' | 'pages' | 'elements';

type Props = {
    violations: Violation[];
    // The page URL, for the AI prompt header (single report).
    url?: string;
    // Page URLs to filter by (website aggregate); also enables the "pages" sort.
    pages?: string[];
    previewEnabled?: boolean;
};

function isWebsite(v: Violation): v is WebsiteAxeResult {
    return (v as WebsiteAxeResult).reports !== undefined;
}

function elementCount(v: Violation): number {
    return isWebsite(v)
        ? v.reports.reduce((n, r) => n + (r.node_count ?? 0), 0)
        : (v.nodes?.length ?? 0);
}

/**
 * A filterable, sortable list of violations. The filters live in the query string
 * (impact, rule, page, sort, desc), so an email or a website card can link straight to
 * one rule, and a #violation-<rule> hash scrolls to that card (clearing filters that
 * would hide it).
 */
function ViolationsList({ violations, url, pages, previewEnabled = false }: Props) {
    const { params, setFilters } = useUrlFilters();
    const impacts = (params.get('impact') ?? '').split(',').filter(Boolean) as Impact[];
    const ruleQuery = params.get('rule') ?? '';
    const pageFilter = pages ? (params.get('page') ?? '') : '';
    const sortParam = params.get('sort');
    const sortKey: SortKey =
        sortParam === 'impact' || sortParam === 'pages' || sortParam === 'elements'
            ? sortParam
            : pages
              ? 'pages'
              : 'impact';
    const desc = params.get('desc') !== '0';
    const filtering = impacts.length > 0 || !!ruleQuery || !!pageFilter;

    const query = ruleQuery.toLowerCase();
    const shown = violations
        .filter(
            (v) =>
                (impacts.length === 0 || (v.impact !== undefined && impacts.includes(v.impact))) &&
                (!query ||
                    [v.id, v.help, v.description].some((t) => t?.toLowerCase().includes(query))) &&
                (!pageFilter || (isWebsite(v) && v.reports.some((r) => r.url === pageFilter)))
        )
        .sort((a, b) => {
            const value = (v: Violation) =>
                sortKey === 'impact'
                    ? -impactRank(v.impact)
                    : sortKey === 'pages'
                      ? isWebsite(v)
                          ? v.reports.length
                          : 0
                      : elementCount(v);
            return desc ? value(b) - value(a) : value(a) - value(b);
        });

    // Deep links: /reports/1?rule=x#violation-x. Scroll once the card is on the page.
    const scrolled = useRef(false);
    useEffect(() => {
        if (scrolled.current || !window.location.hash.startsWith('#violation-')) return;
        const id = decodeURIComponent(window.location.hash.slice('#violation-'.length));
        if (!shown.some((v) => v.id === id)) {
            if (filtering) setFilters({ impact: null, rule: null, page: null });
            return;
        }
        scrolled.current = true;
        document.getElementById(`violation-${id}`)?.scrollIntoView({ block: 'start' });
    });

    const clear = () => setFilters({ impact: null, rule: null, page: null });

    return (
        <div>
            <Flex gap={12} align="center" wrap="wrap" className="mb-4">
                <Select
                    mode="multiple"
                    allowClear
                    placeholder="Any impact"
                    style={{ minWidth: 220 }}
                    aria-label="Filter by impact"
                    value={impacts}
                    options={IMPACTS.map((m) => ({ value: m.key, label: m.label }))}
                    onChange={(value: Impact[]) => setFilters({ impact: value.join(',') || null })}
                />
                <Input.Search
                    allowClear
                    placeholder="Search rules"
                    style={{ width: 240 }}
                    aria-label="Search rules"
                    key={ruleQuery}
                    defaultValue={ruleQuery}
                    onSearch={(value) => setFilters({ rule: value || null })}
                />
                {pages && (
                    <Select
                        allowClear
                        showSearch
                        placeholder="Any page"
                        style={{ minWidth: 280 }}
                        aria-label="Filter by page"
                        value={pageFilter || undefined}
                        options={pages.map((p) => ({ value: p, label: p }))}
                        onChange={(value) => setFilters({ page: value || null })}
                    />
                )}
                <Space>
                    <span className="text-gray-600">Sort by</span>
                    <Select
                        size="small"
                        style={{ minWidth: 150 }}
                        aria-label="Sort by"
                        value={sortKey}
                        options={[
                            { value: 'impact', label: 'Impact' },
                            ...(pages ? [{ value: 'pages', label: 'Pages affected' }] : []),
                            { value: 'elements', label: 'Elements' },
                        ]}
                        onChange={(value: SortKey) => setFilters({ sort: value })}
                    />
                    <Button
                        size="small"
                        onClick={() => setFilters({ desc: desc ? '0' : null })}
                        aria-label={desc ? 'Descending' : 'Ascending'}
                        icon={<span aria-hidden="true">{desc ? '↓' : '↑'}</span>}
                    >
                        {desc ? 'Desc' : 'Asc'}
                    </Button>
                </Space>
                <span className="text-sm text-gray-600">
                    Showing {shown.length} of {violations.length}
                </span>
                {filtering && (
                    <Button size="small" type="link" onClick={clear}>
                        Clear filters
                    </Button>
                )}
                <div className="ml-auto">
                    <GenerateAIPromptButton violations={shown} url={url} />
                </div>
            </Flex>
            {shown.length === 0 ? (
                <div className="py-6 text-center text-gray-500">
                    No violations match the current filters.
                </div>
            ) : (
                shown.map((v) => (
                    <AuditAccessibilityItem
                        key={v.id}
                        accessibilityResult={v}
                        previewEnabled={previewEnabled}
                    />
                ))
            )}
        </div>
    );
}

export default ViolationsList;

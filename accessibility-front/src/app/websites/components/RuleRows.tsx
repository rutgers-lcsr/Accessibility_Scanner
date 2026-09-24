'use client';
import { ImpactTag } from '@/lib/impact';
import { ChangeRule } from '@/lib/types/finding';
import { Tag } from 'antd';

// Rules with their pages, as the What-changed tab and a page rescan summary list them.
export default function RuleRows({ rules, empty }: { rules: ChangeRule[]; empty: string }) {
    if (rules.length === 0) return <div className="text-gray-500">{empty}</div>;
    return (
        <ul style={{ paddingLeft: 0, margin: 0, listStyle: 'none' }}>
            {rules.map((rule) => (
                <li key={rule.rule_id} className="mb-4">
                    <div className="flex flex-wrap items-center gap-2">
                        <ImpactTag impact={rule.impact} />
                        <span className="font-semibold">{rule.rule_id}</span>
                        <span className="text-gray-600">{rule.help}</span>
                        <Tag>
                            {rule.count} {rule.count === 1 ? 'element' : 'elements'}
                        </Tag>
                        {rule.help_url && (
                            <a href={rule.help_url} target="_blank" rel="noopener noreferrer">
                                How to fix
                            </a>
                        )}
                    </div>
                    <ul className="ml-4 mt-1 text-sm">
                        {rule.pages.map((page) => (
                            <li key={page.site_id}>
                                <a
                                    href={`/reports/${page.report_id}?rule=${encodeURIComponent(rule.rule_id)}#violation-${encodeURIComponent(rule.rule_id)}`}
                                >
                                    {page.url}
                                </a>{' '}
                                ({page.count})
                                {page.findings.some((f) => f.reopened) && (
                                    <Tag color="orange" style={{ marginLeft: 8 }}>
                                        reopened
                                    </Tag>
                                )}
                            </li>
                        ))}
                    </ul>
                </li>
            ))}
        </ul>
    );
}

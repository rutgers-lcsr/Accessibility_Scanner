'use client';
import { useGuides } from '@/hooks/useGuides';
import { guideHref } from '@/lib/guides';
import { ImpactTag } from '@/lib/impact';
import { Card } from 'antd';
import Link from 'next/link';

function FixGuidesPage() {
    const { items } = useGuides();
    return (
        <div className="p-4">
            <h2 className="mb-2 text-2xl font-semibold">Fix guides</h2>
            <p className="mb-6 text-gray-600">
                Step-by-step fixes for the most common findings, with notes for WordPress, Canvas,
                GitHub Pages and plain HTML.
            </p>
            <div className="grid grid-cols-[repeat(auto-fit,minmax(18rem,1fr))] gap-4">
                {items.map((guide) => (
                    <Card
                        key={guide.rule_id}
                        title={<Link href={guideHref(guide.rule_id)}>{guide.title}</Link>}
                        extra={<ImpactTag impact={guide.impact} />}
                    >
                        <p className="text-gray-700" style={{ margin: 0 }}>
                            {guide.summary}
                        </p>
                        <div className="mt-2 text-xs text-gray-500">{guide.rule_id}</div>
                    </Card>
                ))}
            </div>
        </div>
    );
}

export default FixGuidesPage;

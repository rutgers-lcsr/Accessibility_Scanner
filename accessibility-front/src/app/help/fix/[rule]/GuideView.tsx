'use client';
import GuideMarkdown from '@/components/GuideMarkdown';
import { ImpactTag } from '@/lib/impact';
import { Guide, PlatformId } from '@/lib/types/guide';
import { Tabs, Tag } from 'antd';
import Link from 'next/link';

type Props = {
    guide: Guide;
    platform: PlatformId;
    onPlatformChange: (platform: PlatformId) => void;
};

const CHECK_SECTION = 'check-your-fix';

// A guide's sections in order, with the platform steps as tabs before "Check your fix".
function GuideView({ guide, platform, onPlatformChange }: Props) {
    const check = guide.sections.find((section) => section.id === CHECK_SECTION);
    const common = guide.sections.filter((section) => section.id !== CHECK_SECTION);
    const activePlatform = guide.platforms.some((p) => p.id === platform)
        ? platform
        : guide.platforms[0]?.id;

    const section = (id: string, heading: string, markdown: string) => (
        <section key={id} aria-labelledby={`guide-${id}`} className="mt-6">
            <h3 id={`guide-${id}`} className="text-lg font-semibold">
                {heading}
            </h3>
            <GuideMarkdown markdown={markdown} />
        </section>
    );

    return (
        <article className="max-w-4xl">
            <h2 className="text-2xl font-semibold">{guide.title}</h2>
            <div className="mt-2 flex flex-wrap items-center gap-2">
                <ImpactTag impact={guide.impact} />
                {guide.wcag.map((criterion) => (
                    <Tag key={criterion}>WCAG {criterion}</Tag>
                ))}
                <span className="text-xs text-gray-500">{guide.rule_id}</span>
            </div>
            {guide.summary && <p className="mt-3 text-gray-700">{guide.summary}</p>}

            {common.map((s) => section(s.id, s.heading, s.markdown))}

            {guide.platforms.length > 0 && (
                <section aria-labelledby="guide-platforms" className="mt-6">
                    <h3 id="guide-platforms" className="text-lg font-semibold">
                        Fix it on your platform
                    </h3>
                    <Tabs
                        activeKey={activePlatform}
                        onChange={(key) => onPlatformChange(key as PlatformId)}
                        items={guide.platforms.map((p) => ({
                            key: p.id,
                            label: p.label,
                            children: <GuideMarkdown markdown={p.markdown} />,
                        }))}
                    />
                </section>
            )}

            {check && section(check.id, check.heading, check.markdown)}

            <footer className="mt-8 flex flex-wrap gap-4 text-sm">
                {guide.deque && (
                    <a href={guide.deque} target="_blank" rel="noopener noreferrer">
                        Deque&apos;s reference for {guide.rule_id}
                    </a>
                )}
                <Link href="/help/fix">All fix guides</Link>
            </footer>
        </article>
    );
}

export default GuideView;

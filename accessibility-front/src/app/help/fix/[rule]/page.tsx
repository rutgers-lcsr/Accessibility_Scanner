import type { Metadata } from 'next';
import FixGuide from './FixGuide';

// The browser tab names the rule being fixed ("color-contrast – How to fix – A11y").
export async function generateMetadata({
    params,
}: {
    params: Promise<{ rule: string }>;
}): Promise<Metadata> {
    const { rule } = await params;
    return { title: `${decodeURIComponent(rule)} – How to fix` };
}

async function Page({ params }: { params: Promise<{ rule: string }> }) {
    const { rule } = await params;
    return <FixGuide ruleId={rule} />;
}

export default Page;

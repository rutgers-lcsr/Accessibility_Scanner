import FixGuide from './FixGuide';

async function Page({ params }: { params: Promise<{ rule: string }> }) {
    const { rule } = await params;
    return <FixGuide ruleId={rule} />;
}

export default Page;

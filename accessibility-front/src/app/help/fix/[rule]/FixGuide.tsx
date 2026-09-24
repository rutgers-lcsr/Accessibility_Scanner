'use client';
import PageError from '@/components/PageError';
import PageLoading from '@/components/PageLoading';
import { APIError, fetcherApi } from '@/lib/api';
import { PLATFORM_STORAGE_KEY, isPlatformId } from '@/lib/guides';
import { Guide, PlatformId } from '@/lib/types/guide';
import { useUrlFilters } from '@/lib/urlFilters';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import useSWR from 'swr';
import GuideView from './GuideView';

// One guide. The platform tab comes from ?platform=, else the browser's remembered
// choice, else plain HTML; picking one updates both.
function FixGuide({ ruleId }: { ruleId: string }) {
    const { params, setFilters } = useUrlFilters();
    const [stored, setStored] = useState<PlatformId | null>(null);
    useEffect(() => {
        try {
            const value = localStorage.getItem(PLATFORM_STORAGE_KEY);
            if (isPlatformId(value)) setStored(value);
        } catch {
            // private mode or blocked storage: the default applies
        }
    }, []);

    const { data, error, isLoading } = useSWR<Guide>(
        `/api/guides/${encodeURIComponent(ruleId)}`,
        fetcherApi<Guide>
    );

    if (error) {
        const missing = (error as APIError).response?.status === 404;
        return (
            <div>
                <PageError
                    status={missing ? 404 : 500}
                    title={missing ? 'No guide for this rule yet' : 'Error loading the guide'}
                    subTitle={
                        missing
                            ? "Deque's reference for the rule is linked from the violation itself."
                            : undefined
                    }
                />
                <p className="text-center">
                    <Link href="/help/fix">All fix guides</Link>
                </p>
            </div>
        );
    }
    if (isLoading || !data) return <PageLoading />;

    const fromUrl = params.get('platform');
    const platform = isPlatformId(fromUrl) ? fromUrl : (stored ?? 'html');
    const choose = (id: PlatformId) => {
        try {
            localStorage.setItem(PLATFORM_STORAGE_KEY, id);
        } catch {
            // remembered for this page only
        }
        setStored(id);
        setFilters({ platform: id });
    };

    return (
        <div className="p-4">
            <GuideView guide={data} platform={platform} onPlatformChange={choose} />
        </div>
    );
}

export default FixGuide;

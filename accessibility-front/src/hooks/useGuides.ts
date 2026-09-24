'use client';
import { fetcherApi } from '@/lib/api';
import { GuideIndex, GuideIndexItem } from '@/lib/types/guide';
import useSWR from 'swr';

// Which rules have a fix guide. Public data, fetched once and shared by every card.
export function useGuides(): { items: GuideIndexItem[]; has: (ruleId: string) => boolean } {
    const { data } = useSWR<GuideIndex>('/api/guides', fetcherApi<GuideIndex>, {
        revalidateOnFocus: false,
    });
    const items = data?.items ?? [];
    return { items, has: (ruleId) => items.some((item) => item.rule_id === ruleId) };
}

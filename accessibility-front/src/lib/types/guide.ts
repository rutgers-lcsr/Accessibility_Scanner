import type { Impact } from './dashboard';

// Fix guides (GET /api/guides): our own "how to fix" per axe rule, with a tab per platform.
export type PlatformId = 'wordpress' | 'canvas' | 'github-pages' | 'html';

export type GuideSection = { id: string; heading: string; markdown: string };
export type GuidePlatform = { id: PlatformId; label: string; markdown: string };

export type Guide = {
    rule_id: string;
    title: string;
    impact: Impact | null;
    summary: string;
    wcag: string[];
    deque: string | null;
    markdown: string;
    sections: GuideSection[];
    platforms: GuidePlatform[];
};

export type GuideIndexItem = Pick<Guide, 'rule_id' | 'title' | 'impact' | 'summary'>;
export type GuideIndex = { count: number; items: GuideIndexItem[] };

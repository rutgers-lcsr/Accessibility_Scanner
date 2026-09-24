import type { PlatformId } from './types/guide';

export const PLATFORMS: { id: PlatformId; label: string }[] = [
    { id: 'wordpress', label: 'WordPress' },
    { id: 'canvas', label: 'Canvas' },
    { id: 'github-pages', label: 'GitHub Pages' },
    { id: 'html', label: 'Plain HTML' },
];

// The platform a person picked on a guide page, kept per browser.
export const PLATFORM_STORAGE_KEY = 'a11y:guide-platform';

export function isPlatformId(value: string | null | undefined): value is PlatformId {
    return PLATFORMS.some((platform) => platform.id === value);
}

/** A platform suggested by a website's categories ("canvas", "wordpress", "github"). */
export function platformHint(categories: string[]): PlatformId | null {
    const text = categories.join(' ').toLowerCase();
    if (/canvas/.test(text)) return 'canvas';
    if (/wordpress|\bwp\b/.test(text)) return 'wordpress';
    if (/github|jekyll/.test(text)) return 'github-pages';
    return null;
}

export function guideHref(ruleId: string, platform?: PlatformId | null): string {
    const base = `/help/fix/${encodeURIComponent(ruleId)}`;
    return platform ? `${base}?platform=${platform}` : base;
}

/** The website's Violations tab, filtered to and scrolled to one rule. */
export function violationsHref(websiteId: number, ruleId: string): string {
    const id = encodeURIComponent(ruleId);
    return `/websites/${websiteId}?tab=violations&rule=${id}#violation-${id}`;
}

/** One page's report, scrolled to the rule; null when the page has no report. */
export function reportHref(reportId: number | null, ruleId: string): string | null {
    if (reportId === null) return null;
    const id = encodeURIComponent(ruleId);
    return `/reports/${reportId}?rule=${id}#violation-${id}`;
}

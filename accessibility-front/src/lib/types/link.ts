// A link found on a website's pages (any host) and whether its target responds
// (GET /api/websites/<id>/links).
export type LinkStatus = 'pending' | 'ok' | 'broken' | 'blocked' | 'error' | 'skipped';

// A page the link is on, with the text of the link there and the page's latest report.
export type LinkSource = {
    url: string;
    text: string | null;
    site_id: number;
    report_id: number | null;
};

export type WebsiteLink = {
    id: number;
    website_id: number;
    url: string;
    external: boolean;
    status: LinkStatus;
    status_code: number | null;
    // set only when the link redirected
    final_url: string | null;
    error: string | null;
    first_seen: string;
    last_seen: string;
    checked_at: string | null;
    found_on: LinkSource[];
    found_on_count: number;
};

// One page's links (GET /api/sites/<id>/links): the same check result plus the link
// text on that page.
export type PageLink = Pick<WebsiteLink, 'id' | 'url' | 'external' | 'status' | 'status_code' | 'final_url' | 'error' | 'checked_at'> & {
    text: string | null;
};

export type LinkCounts = {
    total: number;
    broken: number;
};

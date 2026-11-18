export type CaptionStatus = 'present' | 'missing' | 'unknown';

export type MediaItem = {
    id: number;
    url: string;
    kind: 'video' | 'audio' | 'embed';
    provider: string | null;
    captions: CaptionStatus;
    caption_override: 'verified' | 'missing' | null;
    caption_status: CaptionStatus;
    audio_description: boolean;
    note: string | null;
    override_by: string | null;
    override_at: string | null;
    first_seen: string;
    last_seen: string;
    pages: string[];
};

export type VendorStatus = 'approved' | 'under_review' | 'not_approved';

export const VENDOR_STATUS_LABELS: Record<VendorStatus, string> = {
    approved: 'Approved',
    under_review: 'Under review',
    not_approved: 'Not approved',
};

export type VendorSummary = {
    id: number;
    name: string;
    status: VendorStatus;
    has_vpat: boolean;
    review_overdue: boolean;
};

export type ThirdPartyHost = {
    id: number;
    host: string;
    kinds: string[];
    example_url: string | null;
    page_count: number;
    pages: string[];
    first_seen: string;
    last_seen: string;
    vendor: VendorSummary | null;
};

export type Vendor = {
    id: number;
    name: string;
    hosts: string[];
    status: VendorStatus;
    vpat_url: string | null;
    vpat_date: string | null;
    review_due: string | null;
    review_overdue: boolean;
    contact: string | null;
    notes: string | null;
    websites?: number;
    // The websites using it that the viewer may see, most pages first.
    sites?: VendorSite[];
};

export type VendorSite = {
    website_id: number;
    url: string;
    // The vendor's hosts this website uses.
    hosts: string[];
    pages: number;
    kinds: string[];
};

export type UnassignedHostSite = {
    website_id: number;
    url: string;
    pages: number;
    kinds: string[];
    // A few of the website's pages that use the host.
    example_pages: string[];
};
export type UnassignedHost = {
    host: string;
    websites: number;
    pages: number;
    kinds: string[];
    // The websites using it, most pages first.
    sites: UnassignedHostSite[];
};

export type PageContent = {
    site_id: number;
    url: string;
    report_id: number | null;
    content_changed_at: string | null;
    last_modified: string | null;
    stale: boolean;
    mixed_content: { url: string; tag: string }[];
};

export type PageContentList = {
    count: number;
    stale_after_days: number;
    items: PageContent[];
};

export type MediaCounts = { total: number; missing: number; unknown: number };
export type ContentCounts = {
    stale_pages: number;
    mixed_content_pages: number;
    last_change: string | null;
};

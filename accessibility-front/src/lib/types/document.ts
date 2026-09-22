// A PDF, Word, PowerPoint or Excel file linked from a website's pages
// (GET /api/websites/<id>/documents).
export type DocumentStatus =
    | 'pending'
    | 'tagged'
    | 'untagged'
    | 'unreachable'
    | 'too_large'
    | 'unreadable'
    | 'skipped'
    | 'not_checked';

export type WebsiteDocument = {
    id: number;
    website_id: number;
    url: string;
    type: 'pdf' | 'doc' | 'docx' | 'ppt' | 'pptx' | 'xls' | 'xlsx';
    status: DocumentStatus;
    first_seen: string;
    last_seen: string;
    checked_at: string | null;
    size_bytes: number | null;
    page_count: number | null;
    title: string | null;
    has_title: boolean | null;
    language: string | null;
    error: string | null;
    found_on: string[];
    found_on_count: number;
};

export type DocumentCounts = {
    total: number;
    pdf: number;
    untagged_pdf: number;
    unchecked: number;
};

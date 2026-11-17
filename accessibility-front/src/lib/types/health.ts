export type RequirementResult = {
    id: number;
    name: string;
    passed: boolean;
    detail: string | null;
};

export type WebsiteHealth = {
    checked_at: string;
    up: boolean;
    up_changed_at: string | null;
    status_code: number | null;
    response_ms: number | null;
    error: string | null;
    final_url: string | null;
    https_redirect: boolean | null;
    tls_valid: boolean | null;
    tls_expires_at: string | null;
    tls_issuer: string | null;
    tls_error: string | null;
    tls_days_left?: number;
    tls_expiring?: boolean;
    security_headers: Record<string, string | null>;
    platform: string | null;
    platform_version: string | null;
    server: string | null;
    requirements: RequirementResult[];
};

export type HealthCheck = {
    checked_at: string;
    up: boolean;
    status_code: number | null;
    response_ms: number | null;
    error: string | null;
};

export type HealthSummary = {
    health: WebsiteHealth | null;
    uptime: { day: number | null; week: number | null; month: number | null; checks: number };
    recent: HealthCheck[];
    requirements: { id: number; name: string }[];
    security_headers: string[];
};

export type RequirementCheckType = 'link_text' | 'link_href' | 'selector' | 'text';

export const CHECK_TYPE_LABELS: Record<RequirementCheckType, string> = {
    link_text: 'A link whose text matches',
    link_href: 'A link whose address matches',
    selector: 'An element matching the CSS selector',
    text: 'Page text matching',
};

export type ContentRequirement = {
    id: number;
    name: string;
    description: string | null;
    check_type: RequirementCheckType;
    pattern: string;
    enabled: boolean;
    website_ids: number[];
};

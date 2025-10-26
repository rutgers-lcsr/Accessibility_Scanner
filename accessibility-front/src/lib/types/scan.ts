export type scanResponse = {
    message: string;
    info?: string;
    task_id: string;
    status_endpoint: string;
    polling_endpoint: string;
};

export type TaskStatus = {
    state: 'PENDING' | 'PROGRESS' | 'SUCCESS' | 'FAILURE' | 'RETRY' | 'REVOKED';
    status?: string;
    current?: number;
    total?: number;
    result?: {
        status: string;
        website_url: string;
        reports_generated: number;
        sites_scanned: number;
    };
};

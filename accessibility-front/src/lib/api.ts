export const fetcherApi = <T>(url: string) => handleRequest<T>(url);

export const handleRequest = async <T>(url: string, options?: RequestInit): Promise<T> => {
    const response = await fetch(url, options);
    if (!response.ok) {
        let reason = await response.json().catch(() => ({ error: 'Unknown error' }));
        if (response.status == 404) {
            reason = { error: 'Not Found' };
        }

        throw new APIError(response, reason.error || 'API request failed', reason);
    }
    return response.json();
};

export class APIError extends Error {
    response: Response;
    message: string;
    // The parsed error body, when the API sent one (e.g. { error, code, domain })
    details: Record<string, unknown>;

    constructor(response: Response, message?: string, details: Record<string, unknown> = {}) {
        super(message);
        this.response = response;
        this.message = message || 'API request failed';
        this.details = details;
    }
    getReason() {
        return this.message;
    }
    toString() {
        return this.response.status + ' ' + this.response.statusText + ': ' + this.message;
    }
}

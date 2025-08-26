export const fetcherApi = <T>(url: string) => handleRequest<T>(url);

export const handleRequest = async <T>(url: string, options?: RequestInit): Promise<T> => {
    const response = await fetch(url, options);
    if (!response.ok) {
        const reason = await response.json();

        throw new APIError(response, reason.error || 'API request failed');
    }
    return response.json();
};

export class APIError extends Error {
    response: Response;
    message: string;

    constructor(response: Response, message?: string) {
        super(response.statusText);
        this.response = response;
        this.message = message || 'API request failed';
    }
    getReason() {
        return this.message;
    }
    toString() {
        return this.response.status + ' ' + this.response.statusText + ': ' + this.message;
    }
}

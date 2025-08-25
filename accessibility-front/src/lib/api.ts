export const fetcherApi = <T>(url: string) => handleRequest<T>(url);

export const APIURL =
    process.env.NODE_ENV == 'development'
        ? 'http://localhost:5000'
        : process.env.NEXT_PUBLIC_FLASK_API_URL;

export const handleRequest = async <T>(url: string, options?: RequestInit): Promise<T> => {
    const requested_url = APIURL + url;

    const response = await fetch(requested_url, options);
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

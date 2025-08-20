export const handleRequest = async <T>(url: string, options?: RequestInit): Promise<T> => {
    let requested_url = process.env.NEXT_PUBLIC_FLASK_API_URL + url;

    if (process.env.NODE_ENV == "development") {
        requested_url = "http://localhost:5000" + url;
    }

    const response = await fetch(requested_url, options);
    if (!response.ok) {
        const reason = await response.json();

        throw new APIError(response, reason.message || "API request failed");
    }
    return response.json();
};

export class APIError extends Error {
    response: Response;
    message: string;

    constructor(response: Response, message?: string) {
        super(response.statusText);
        this.response = response;
        this.message = message || "API request failed";
    }
    getReason() {
        return this.message;
    }
    toString() {
        return this.response.status + " " + this.response.statusText + ": " + this.message;
    }
}

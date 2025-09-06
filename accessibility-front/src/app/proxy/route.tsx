import ProxyError from '@/components/ProxyError';
import { NextRequest, NextResponse } from 'next/server';

function makeHtmlPage(body: string) {
    if (body.includes('<html')) {
        return body;
    }
    if (body.includes('<body')) {
        return `
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Accessibility Report</title>
        </head>
        ${body}
        </html>`;
    }

    return `
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Accessibility Report</title>
        </head>
        <body>
            <pre>${body}</pre>
        </body>
        </html>
    `;
}

function injectScript(body: string, url: string, reportId: string) {
    const reportScript = `<script defer src="${process.env.NEXT_PUBLIC_BASE_URL}/api/reports/${reportId}/script/"></script>`;
    let html = makeHtmlPage(body);

    html = html.replace(/href="([^"]+)"/g, (match, p1) => {
        const newUrl = new URL(p1, url).href;
        return `href="${newUrl}"`;
    });

    html = html.replace(/src="([^"]+)"/g, (match, p1) => {
        const newUrl = new URL(p1, url).href;
        return `src="${newUrl}"`;
    });

    html = html.replace('</head>', `${reportScript}</head>`);

    return html;
}

function proxyError(status: Response['status']) {
    switch (status) {
        case 400:
            return (
                <ProxyError
                    status={400}
                    title="Bad Request"
                    subTitle="The request was invalid or malformed. Please check the URL and try again."
                    details="This error usually means the server could not understand your request."
                />
            );
        case 401:
            return (
                <ProxyError
                    status={401}
                    title="Unauthorized"
                    subTitle="Access denied due to missing or invalid credentials."
                    details="You may need to log in or provide authentication to view this website."
                />
            );
        case 403:
            return (
                <ProxyError
                    status={403}
                    title="Forbidden"
                    subTitle="You do not have permission to access this website."
                    details="The server understood your request but refuses to authorize it. This may be due to site restrictions or security policies."
                />
            );
        case 404:
            return (
                <ProxyError
                    status={404}
                    title="Not Found"
                    subTitle="The requested website could not be found."
                    details="The URL may be incorrect or the site may no longer exist."
                />
            );
        case 405:
            return (
                <ProxyError
                    status={405}
                    title="Method Not Allowed"
                    subTitle="The HTTP method used is not allowed for this resource."
                    details="Please check the request type and try again."
                />
            );
        case 429:
            return (
                <ProxyError
                    status={429}
                    title="Too Many Requests"
                    subTitle="The website is rate limiting requests. Please try again later."
                    details="You have sent too many requests in a given amount of time."
                />
            );
        case 500:
            return (
                <ProxyError
                    status={500}
                    title="Server Error"
                    subTitle="An unexpected error occurred on the server."
                    details="Please try again later or contact support if the issue persists."
                />
            );
        case 502:
            return (
                <ProxyError
                    status={502}
                    title="Bad Gateway"
                    subTitle="Received an invalid response from the upstream server."
                    details="This may be a temporary issue with the website or network."
                />
            );
        default:
            return (
                <ProxyError
                    status={status}
                    title={`Error ${status}`}
                    subTitle="An error occurred while accessing the website."
                    details="No further information is available."
                />
            );
    }
}

export async function GET(req: NextRequest) {
    const searchParams = req.nextUrl.searchParams;

    const url = searchParams.get('url') || '';
    const reportId = searchParams.get('reportId') || '';
    const { renderToString } = await import('react-dom/server');

    try {
        const response = await fetch(url);

        if (!response.ok) {
            return new NextResponse(renderToString(proxyError(response.status)), {
                status: response.status,
                headers: { 'Content-Type': 'text/html' },
            });
        }

        let body = await response.text();

        // If the reportId is present, we can use it to modify the response
        if (reportId) {
            body = injectScript(body, url, reportId);
        }

        return new NextResponse(body, {
            headers: {
                'Content-Type': response.headers.get('content-type') || 'text/html',
                'X-Frame-Options': 'ALLOWALL',
            },
        });
    } catch (err) {
        console.log(err);

        if (err instanceof TypeError) {
            return new NextResponse(renderToString(proxyError(502)), {
                status: 502,
                headers: { 'Content-Type': 'text/html' },
            });
        }

        return new NextResponse(renderToString(proxyError(500)), {
            status: 500,
            headers: { 'Content-Type': 'text/html' },
        });
    }
}

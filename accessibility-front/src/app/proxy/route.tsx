import ProxyError from '@/components/ProxyError';
import axios from 'axios';
import https from 'https';
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

function redirectUrl(url: string, link: string, linkType: 'href' | 'src') {
    if (link.startsWith('http') || link.startsWith('https')) {
        return link; // Don't change absolute URLs
    }
    if (link.startsWith('data:')) {
        return link; // Don't change data URLs
    }
    if (link.startsWith('//')) {
        return link; // Don't change protocol-relative URLs
    }
    // this is the hard part, links are usually handled relative to the base URL of the page, but we need to make it an absolute URL
    let baseUrl = url;

    // if baseUrl ends with a file (e.g. .html, .php, .aspx, etc.), remove the file part
    const endsWithFile = baseUrl.match(/\/[^\/]+\.[a-zA-Z0-9]+$/);
    if (endsWithFile) {
        baseUrl = baseUrl.substring(0, baseUrl.lastIndexOf('/'));
    }
    if (!baseUrl.endsWith('/') && !link.startsWith('/')) {
        baseUrl = baseUrl + '/';
    }

    const newUrl = new URL(link, baseUrl).href;
    console.log(`Redirecting ${linkType} from ${link} to ${newUrl}`);
    return newUrl;
}

function injectScript(body: string, url: string, reportId: string) {
    const reportScript = `<script defer src="${process.env.NEXT_PUBLIC_BASE_URL}/api/reports/${reportId}/script/"></script>`;
    let html = makeHtmlPage(body);

    html = html.replace(/href="([^"]+)"/g, (match, p1) => {
        return `href="${redirectUrl(url, p1, 'href')}"`;
    });

    html = html.replace(/src="([^"]+)"/g, (match, p1) => {
        return `src="${redirectUrl(url, p1, 'src')}"`;
    });

    // for the single page without a head tag, we need to add one
    if (!html.includes('</head>')) {
        // if there is no head tag, we need to add one
        html = html.replace(/<html([^>]*)>/, `<html$1><head>${reportScript}</head>`);

        if (!html.includes('<head>')) {
            // if there is no head tag, we need to add one
            html = html.replace(/<body([^>]*)>/, `<body$1><head>${reportScript}</head>`);
        }
        if (!html.includes('<head>')) {
            // if there is still no head tag, we need to add one at the top
            html = html.replace(/<html([^>]*)>/, `<html$1><head>${reportScript}</head><body>`);
        }

        return html;
    }
    html = html.replace('</head>', `${reportScript} </head>`);

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
                    details="This may be a temporary issue with the website or network. This could be due to SSL issues or the server being down. If it is an SSL issue, please ensure the site has a valid SSL certificate. Or use the following extension to bypass CORS and SSL issues."
                    link="https://chromewebstore.google.com/detail/axe-devtools-web-accessib/lhdoppojpmngadmnindnejefpokejbdd"
                    linkName="Axe DevTools Extension"
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
        const requestHeaders = new Headers();
        requestHeaders.set('User-Agent', req.headers.get('User-Agent') || 'Mozilla/5.0');
        requestHeaders.set(
            'Accept-Language',
            req.headers.get('Accept-Language') || 'en-US,en;q=0.9'
        );
        requestHeaders.set('Accept', req.headers.get('Accept') || '*/*');

        const agent = new https.Agent({
            rejectUnauthorized: false,
        });
        const response = await axios.get(url, {
            headers: Object.fromEntries(requestHeaders.entries()),
            httpsAgent: agent,
            responseType: 'text',
            validateStatus: () => true,
        });

        if (!response.status || response.status >= 400) {
            return new NextResponse(renderToString(proxyError(response.status)), {
                status: response.status,
                headers: { 'Content-Type': 'text/html' },
            });
        }

        let body = await response.data;

        // If the reportId is present, we can use it to modify the response
        if (reportId) {
            body = injectScript(body, url, reportId);
        }
        if (!body) {
            body = '<html><body><h1>No content</h1></body></html>';
        }

        return new NextResponse(body, {
            headers: {
                'Content-Type': response.headers
                    ? response.headers['content-type'] || 'text/html'
                    : 'text/html',
                'Access-Control-Allow-Origin': '*',
                'Content-Security-Policy': "frame-ancestors 'self' *",
                'X-Frame-Options': 'ALLOWALL',
                'Referrer-Policy': 'no-referrer',
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

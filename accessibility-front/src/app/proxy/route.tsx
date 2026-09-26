import ProxyError from '@/components/ProxyError';
import { Browser, getAxeLink, getCurrentBrowser } from '@/lib/browserServerSide';
import { decodeBody, isHtml, PREVIEW_COOKIE, rewritePage, textPage } from '@/lib/proxyRewrite';
import { fetchPublicUrl, UnsafeTargetError } from '@/lib/safeTarget';
import { Report as ReportType } from '@/lib/types/axe';
import { User } from '@/lib/types/user';
import axios from 'axios';
import { getCurrentUser } from 'next-cas-client/app';
import { NextRequest, NextResponse } from 'next/server';

const MAX_PAGE_BYTES = 10 * 1024 * 1024;

function proxyError(status: Response['status'], browser?: Browser) {
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
            const link = getAxeLink(browser as 'Chrome' | 'Firefox' | null);

            return (
                <ProxyError
                    status={502}
                    title="Bad Gateway"
                    subTitle="Received an invalid response from the upstream server."
                    details="This may be a temporary issue with the website or network. This could be due to SSL issues or the server being down. If it is an SSL issue, please ensure the site has a valid SSL certificate. Or use the following extension to bypass CORS and SSL issues."
                    link={link}
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

async function fetchReport(reportId: string): Promise<{ status: number; report?: ReportType }> {
    const user = await getCurrentUser<User>();
    const response = await fetch(`${process.env.API_URL}/api/reports/${reportId}/`, {
        headers: user ? { Authorization: `Bearer ${user.access_token || ''}` } : {},
        cache: 'no-store',
    });
    if (!response.ok) {
        return { status: response.status };
    }
    return { status: 200, report: (await response.json()) as ReportType };
}

export async function GET(req: NextRequest) {
    const searchParams = req.nextUrl.searchParams;
    const reportId = searchParams.get('report') || '';
    const url = searchParams.get('url') || '';
    const { renderToString } = await import('react-dom/server');
    const userAgent = req.headers.get('User-Agent') || 'Mozilla/5.0';

    const browser = getCurrentBrowser(userAgent);
    const errorPage = (status: number) =>
        new NextResponse(renderToString(proxyError(status, browser)), {
            status,
            headers: { 'Content-Type': 'text/html' },
        });

    // The target is never taken from the query alone: it must be the URL of a report the
    // current user may view, so this route cannot be pointed at arbitrary hosts. The
    // report also supplies the script token, which therefore never appears in page URLs.
    if (!/^\d+$/.test(reportId)) {
        return errorPage(400);
    }
    const { status, report } = await fetchReport(reportId);
    if (!report) {
        return errorPage(status === 401 ? 403 : status);
    }
    if (report.url !== url) {
        return errorPage(400);
    }
    const scriptSrc = `${process.env.NEXT_PUBLIC_BASE_URL}/api/reports/script/${report.script_token}/`;

    try {
        const requestHeaders = new Headers();
        requestHeaders.set('User-Agent', userAgent);
        requestHeaders.set(
            'Accept-Language',
            req.headers.get('Accept-Language') || 'en-US,en;q=0.9'
        );
        requestHeaders.set('Accept', req.headers.get('Accept') || '*/*');

        // Public hosts only, certificate verification on, every redirect hop checked.
        const response = await fetchPublicUrl(url, {
            headers: Object.fromEntries(requestHeaders.entries()),
            responseType: 'arraybuffer',
            maxContentLength: MAX_PAGE_BYTES,
        });

        if (!response.status || response.status >= 400) {
            return errorPage(response.status);
        }

        // Only this app may frame the preview.
        const headers: Record<string, string> = {
            'Content-Security-Policy': "frame-ancestors 'self'",
            'X-Content-Type-Options': 'nosniff',
        };
        const contentType = String(response.headers?.['content-type'] || '');
        const bytes = new Uint8Array(response.data);
        if (contentType && !/^text\/|html|xml|json|javascript/i.test(contentType)) {
            // A PDF, an image: nothing to inject into, serve it as it is.
            return new NextResponse(bytes, {
                headers: { ...headers, 'Content-Type': contentType },
            });
        }

        // Links resolve against the page the browser would have ended up on.
        const finalUrl = String(response.config?.url || url);
        const text = decodeBody(bytes, contentType);
        const html = rewritePage(
            isHtml(contentType, text) ? text : textPage(text),
            finalUrl,
            scriptSrc
        );

        const page = new NextResponse(html, {
            headers: { ...headers, 'Content-Type': 'text/html; charset=utf-8' },
        });
        // The page moves to its own path (previewGuard), which takes /proxy out of its
        // Referer; the middleware then finds the site from this cookie.
        page.cookies.set(PREVIEW_COOKIE, finalUrl, {
            path: '/',
            httpOnly: true,
            sameSite: 'strict',
            secure: (process.env.NEXT_PUBLIC_BASE_URL || '').startsWith('https:'),
        });
        return page;
    } catch (err) {
        if (err instanceof UnsafeTargetError) {
            return errorPage(403);
        }
        if (axios.isAxiosError(err) || err instanceof TypeError) {
            return errorPage(502);
        }
        return errorPage(500);
    }
}

import Console from '@/components/Console';
import { Report as ReportType } from '@/lib/types/axe';
import { PageLink } from '@/lib/types/link';
import { CheckCircleFilled, ExclamationCircleOutlined } from '@/lib/icons';

import AuditAccessibilityItem from '@/components/AuditAccessibilityItem';
import ImpactTiles from '@/components/ImpactTiles';
import PageError from '@/components/PageError';
import PageHeading from '@/components/PageHeading';
import PageLinks from '@/components/PageLinks';
import RescanPageButton from '@/components/RescanPageButton';
import ViolationsList from '@/components/ViolationsList';
import { User } from '@/lib/types/user';
import { Alert, Button, Card, Space } from 'antd';
import Content from '@/components/Content';
import { getCurrentUser } from 'next-cas-client/app';
import HeaderLink from './components/HeaderLink';
import PageViews from './components/PageViews';
import ReportDate from './components/ReportDate';

// The reason this is a server component and the rest of them are not, is that all of them should have been really :0
const getReport = async (reportId: string) => {
    // need to forward the request as if we are the user
    // Theres an isssue with headers for some reason out of out control. the type is messed up

    const user = await getCurrentUser<User>();

    const options = {
        headers: user && {
            Authorization: `Bearer ${user.access_token || ''}`,
        },
    };

    const response = await fetch(
        `${process.env.API_URL}/api/reports/${reportId}/`,
        options as RequestInit
    );

    if (!response.ok) {
        if (response.status === 404) return null;
        if (response.status === 403) return "You don't have access to this report";
        return 'Error fetching report';
    }
    return response.json() as Promise<ReportType>;
};

// The page's links with their check results; an empty list when they cannot be loaded,
// so the report still renders.
const getPageLinks = async (siteId: number): Promise<PageLink[]> => {
    const user = await getCurrentUser<User>();
    const options = {
        headers: user && {
            Authorization: `Bearer ${user.access_token || ''}`,
        },
    };
    try {
        const response = await fetch(
            `${process.env.API_URL}/api/sites/${siteId}/links/`,
            options as RequestInit
        );
        if (!response.ok) return [];
        return ((await response.json()) as { items: PageLink[] }).items;
    } catch {
        return [];
    }
};

const plural = (count: number, noun: string) => `${count} ${noun}${count === 1 ? '' : 's'}`;

function hostOf(url: string): string {
    try {
        return new URL(url).host;
    } catch {
        return '';
    }
}

// Most severe first. lib/impact has the same order, but it is a client module.
const IMPACT_RANK: Record<string, number> = { critical: 0, serious: 1, moderate: 2, minor: 3 };
const impactRank = (impact?: string) => IMPACT_RANK[impact ?? ''] ?? 4;

async function Report({ params }: { params: Promise<{ reportId: string }> }) {
    const { reportId } = await params;

    const report = await getReport(reportId);
    if (typeof report === 'string') return <PageError title={report} status={403} />;
    if (report === null) return <PageError status={404} />;
    if (!report) return <PageError status={404} />;

    const violations = report.report_counts.violations;
    const links = await getPageLinks(report.site_id);
    const issues = report.report.violations;
    const toCheck = [...(report.report.incomplete ?? [])].sort(
        (a, b) => impactRank(a.impact) - impactRank(b.impact)
    );
    const website = report.websites?.[0];

    // The scanner followed a redirect (a login page sent to CAS, say): the results are for
    // the page it landed on, which the live preview of the requested address may not show.
    const scannedHost = hostOf(report.base_url);
    const redirected = !!scannedHost && scannedHost !== hostOf(report.url);

    // Built from configuration, not the request's Host header, which a client controls.
    const report_script_full_url = `${process.env.NEXT_PUBLIC_BASE_URL}/api/reports/script/${report.script_token}/`;
    const injectCommand = `var accessScriptElement = document.createElement('script');
accessScriptElement.src = '${report_script_full_url}';
document.body.appendChild(accessScriptElement);`;

    const report_photo_url = `/api/reports/${reportId}/photo/`;

    const reviewCards = toCheck.map((result) => (
        <AuditAccessibilityItem
            key={result.id}
            accessibilityResult={result}
            previewEnabled
            idPrefix="review"
            nodeLabel="Elements to check"
        />
    ));

    // The scanned page, beside the issues on a wide screen (sticky, so "Show in
    // preview" never leaves the list) and after them on a narrow one.
    const pagePanel = (
        <Card>
            <section aria-labelledby="the-page">
                <h2 id="the-page" className="text-xl font-semibold" style={{ margin: '0 0 12px' }}>
                    The page
                </h2>
                <PageViews
                    photoUrl={report_photo_url}
                    photoAlt={`Screenshot of ${report.url} when it was scanned, with the issues outlined`}
                    previewUrl={`/proxy?report=${report.id}&url=${encodeURIComponent(report.url)}`}
                    injectCommand={injectCommand}
                    redirected={redirected}
                />
            </section>
        </Card>
    );

    const injectCard = (
        <Card>
            <h2 className="text-xl font-semibold" style={{ margin: '0 0 8px' }}>
                Inject Script
            </h2>
            <p style={{ margin: '0 0 8px' }}>
                To highlight accessibility issues on the webpage, go to the webpage and copy and
                paste the script below into your browser&apos;s{' '}
                <a
                    href="https://developer.chrome.com/docs/devtools/console/"
                    target="_blank"
                    rel="noopener noreferrer"
                >
                    DevTools Console
                </a>
                .
            </p>
            <p className="text-sm text-gray-600" style={{ margin: '0 0 12px' }}>
                Tip: Open DevTools with <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>K</kbd> (or{' '}
                <kbd>F12</kbd>), then go to the Console tab. You may have to type{' '}
                <span className="font-semibold">allow pasting</span> into the console. Or install
                the axe DevTools{' '}
                <a href="https://chromewebstore.google.com/detail/axe-devtools-web-accessib/lhdoppojpmngadmnindnejefpokejbdd">
                    Chrome extension
                </a>{' '}
                or{' '}
                <a href="https://addons.mozilla.org/en-US/firefox/addon/axe-devtools/">
                    Firefox extension
                </a>
                .
            </p>
            <Console
                id="report-injection-script"
                label="Accessibility Report Script"
                command={injectCommand}
            />
        </Card>
    );

    return (
        <>
            <PageHeading
                title={
                    <>
                        Report for <HeaderLink url={report.url} />
                    </>
                }
                subtitle={
                    <>
                        <ReportDate dateString={report.timestamp} />
                        {website && (
                            <>
                                {' · '}
                                <a href={`/websites/${website.id}`}>
                                    All issues on {hostOf(website.url) || website.url}
                                </a>
                            </>
                        )}
                    </>
                }
                actions={
                    <>
                        {/* The website's admin, its members and site admins. */}
                        {report.can_scan && <RescanPageButton siteId={report.site_id} />}
                        <Button
                            href={`/api/reports/${report.id}/pdf/`}
                            target="_blank"
                            rel="noopener noreferrer"
                        >
                            Download PDF
                        </Button>
                    </>
                }
            />
            <Content className="mb-8 p-4">
                <Space orientation="vertical" size="large" style={{ width: '100%' }}>
                    <Card>
                        <section aria-labelledby="report-verdict">
                            <h2
                                id="report-verdict"
                                className="mb-1 text-2xl font-semibold text-gray-900"
                                style={{ marginTop: 0 }}
                            >
                                {violations.total > 0
                                    ? `${plural(violations.total, 'issue')} to fix on this page`
                                    : 'No issues found by the automated checks'}
                            </h2>
                            <p className="mb-5 text-gray-700">
                                {violations.total > 0 ? (
                                    <a href="#detailed-accessibility-issues">See what to fix</a>
                                ) : (
                                    'Nothing here failed a check.'
                                )}
                                {toCheck.length > 0 && (
                                    <>
                                        {' '}
                                        {violations.total > 0 ? '·' : 'But'}{' '}
                                        <a href="#needs-review">
                                            {plural(toCheck.length, 'check')} need
                                            {toCheck.length === 1 ? 's' : ''} a person to look
                                        </a>
                                        .
                                    </>
                                )}
                            </p>
                            <ImpactTiles
                                counts={violations}
                                listId="detailed-accessibility-issues"
                            />
                            {report.videos.length > 0 && (
                                <p className="text-sm text-gray-700" style={{ margin: '16px 0 0' }}>
                                    <ExclamationCircleOutlined className="mr-1 inline" />
                                    This page has videos: make sure they have captions, and are
                                    labelled with <code>role=&quot;video&quot;</code> and{' '}
                                    <code>aria-label</code>.{' '}
                                    <a
                                        href="https://dequeuniversity.com/rules/axe/4.7/video-caption"
                                        target="_blank"
                                        rel="noopener noreferrer"
                                    >
                                        Learn more
                                    </a>
                                </p>
                            )}
                        </section>
                        {redirected && (
                            <Alert
                                style={{ marginTop: 20 }}
                                type="warning"
                                showIcon
                                title={`When it was scanned, this address redirected to ${scannedHost}`}
                                description={
                                    <>
                                        The results are for the page on {scannedHost}. The live
                                        preview loads {hostOf(report.url)} as it is now and may not
                                        show those issues; the <a href="#the-page">screenshot</a>{' '}
                                        shows the page that was scanned.
                                    </>
                                }
                            />
                        )}
                    </Card>

                    {/* Problem and place side by side on a wide screen. */}
                    <div className="grid grid-cols-1 items-start gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(0,0.9fr)]">
                        <div className="flex min-w-0 flex-col gap-6">
                            <Card>
                                <section aria-labelledby="detailed-accessibility-issues">
                                    <h2
                                        className="mb-1 text-xl font-semibold"
                                        id="detailed-accessibility-issues"
                                        style={{ marginTop: 0 }}
                                    >
                                        What to fix
                                    </h2>
                                    {issues.length > 0 ? (
                                        <>
                                            <p className="mb-4 text-gray-700">
                                                Most severe first. Each issue shows the elements
                                                that failed; <strong>Show in preview</strong> finds
                                                one on the page.
                                            </p>
                                            <ViolationsList
                                                violations={issues}
                                                url={report.url}
                                                previewEnabled
                                                findings={report.findings}
                                                canEdit={report.can_edit}
                                            />
                                        </>
                                    ) : (
                                        // Styled like the theme's success Alert (lib/theme.ts), with the
                                        // heading and text laid out as a block.
                                        <div className="mt-3 flex gap-3 rounded-lg border border-[#a7d5cc] bg-[#e8f5f2] p-4">
                                            <CheckCircleFilled
                                                aria-hidden
                                                style={{
                                                    color: '#00626d',
                                                    fontSize: 18,
                                                    marginTop: 2,
                                                }}
                                            />
                                            <div>
                                                <p
                                                    className="font-semibold text-gray-900"
                                                    style={{ margin: 0 }}
                                                >
                                                    Nothing to fix
                                                </p>
                                                <p
                                                    className="text-gray-700"
                                                    style={{ margin: '4px 0 0' }}
                                                >
                                                    {toCheck.length > 0
                                                        ? 'No element failed an automated check. Some checks need a person to decide; they are listed below.'
                                                        : 'No element failed an automated check on this page.'}
                                                </p>
                                            </div>
                                        </div>
                                    )}
                                </section>
                            </Card>

                            {toCheck.length > 0 && (
                                <Card>
                                    <section aria-labelledby="needs-review">
                                        <h2
                                            id="needs-review"
                                            className="mb-1 text-xl font-semibold"
                                            style={{ marginTop: 0 }}
                                        >
                                            Needs a manual check ({toCheck.length})
                                        </h2>
                                        <p className="mb-4 text-gray-700">
                                            The automated checks could not decide these, often
                                            because of a background image or hidden content. Look at
                                            each element and fix it if the problem applies. They do
                                            not count towards the issues above.
                                        </p>
                                        {issues.length > 0 ? (
                                            // Folded while there is something to fix: these come after it.
                                            <details>
                                                <summary className="cursor-pointer font-medium">
                                                    Show the {plural(toCheck.length, 'check')}
                                                </summary>
                                                <div className="mt-4">{reviewCards}</div>
                                            </details>
                                        ) : (
                                            reviewCards
                                        )}
                                    </section>
                                </Card>
                            )}
                        </div>
                        {/* Stretched to the row so the panel inside has room to stay in view. */}
                        <div className="min-w-0 self-stretch">
                            <div className="xl:sticky xl:top-4">{pagePanel}</div>
                        </div>
                    </div>

                    {injectCard}

                    <Card>
                        <h2
                            className="mb-2 text-xl font-semibold"
                            id="page-links"
                            style={{ marginTop: 0 }}
                        >
                            Links on this page
                        </h2>
                        <p className="mb-4 text-gray-700">
                            Every link found on the page, on this website or elsewhere, and whether
                            it still works.
                        </p>
                        <PageLinks links={links} />
                    </Card>
                </Space>
            </Content>
        </>
    );
}

export default Report;

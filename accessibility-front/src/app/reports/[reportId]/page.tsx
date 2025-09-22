import Console from '@/components/Console';
import { Report as ReportType } from '@/lib/types/axe';
import {
    AlertOutlined,
    ExclamationCircleOutlined,
    InfoCircleOutlined,
    WarningOutlined,
} from '@ant-design/icons';
import { Content } from 'antd/es/layout/layout';
import { headers } from 'next/headers';

import AdminReportItems from '@/components/AdminReportItems';
import AuditAccessibilityItem from '@/components/AuditAccessibilityItem';
import PageError from '@/components/PageError';
import PageLoading from '@/components/PageLoading';
import { User } from '@/lib/types/user';
import { Card, Image, Tooltip } from 'antd';
import { getCurrentUser } from 'next-cas-client/app';
import { Suspense } from 'react';
import HeaderLink from './components/HeaderLink';
import SiteIframe from './components/SiteIframe';

// The reason this is a server component and the rest of them are not, is that all of them should have been really :0
export const getReport = async (reportId: string) => {
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
        throw new Error('Failed to fetch report');
    }
    return response.json() as Promise<ReportType>;
};

async function Report({ params }: { params: Promise<{ reportId: string }> }) {
    const headersList = await headers();
    const host = headersList.get('host');
    const { reportId } = await params;

    const report = await getReport(reportId);
    const user = await getCurrentUser<User>();

    if (!report) return <PageError status={404} />;

    const violations = report.report_counts.violations;

    const report_script_full_url = `https://${host}/api/reports/${reportId}/script/`;

    const report_photo_url = `/api/reports/${reportId}/photo/`;

    return (
        <Content>
            <Content role="main" className="mb-2">
                <Card>
                    <h1 className="mb-2 text-3xl font-extrabold">
                        Report for <HeaderLink url={report.url} />
                    </h1>
                    {user && user.is_admin && <AdminReportItems report={report} />}
                    <h2 className="mb-2 text-lg text-gray-500">
                        Report Date:{' '}
                        {report?.timestamp ? new Date(report.timestamp).toLocaleString() : 'N/A'}
                    </h2>
                    <h3 className="mb-4 text-lg text-gray-500">Website: {report.base_url}</h3>

                    <section
                        role="region"
                        aria-labelledby="accessibility-report"
                        className="rounded-lg bg-gray-50 p-6"
                    >
                        <h2
                            id="accessibility-report"
                            className="mb-6 text-2xl font-semibold text-gray-800"
                        >
                            Accessibility Report
                        </h2>
                        <div className="grid grid-cols-2 gap-6 text-center md:grid-cols-4">
                            <div className="flex flex-col items-center rounded-lg bg-red-50 p-4 shadow-sm">
                                <ExclamationCircleOutlined className="mb-2 text-3xl text-red-700" />
                                <h3 className="mb-2 text-lg font-medium text-red-700">Critical</h3>
                                <h4 className="text-3xl font-bold text-red-600">
                                    {violations.critical}
                                </h4>
                            </div>
                            <div className="flex flex-col items-center rounded-lg bg-red-100 p-4 shadow-sm">
                                <AlertOutlined className="mb-2 text-3xl text-red-700" />
                                <h3 className="mb-2 text-lg font-medium text-red-700">Serious</h3>
                                <h4 className="text-3xl font-bold text-red-600">
                                    {violations.serious}
                                </h4>
                            </div>
                            <div className="flex flex-col items-center rounded-lg bg-orange-50 p-4 shadow-sm">
                                <WarningOutlined className="mb-2 text-3xl text-orange-700" />
                                <h3 className="mb-2 text-lg font-medium text-orange-700">
                                    Moderate
                                </h3>
                                <h4 className="text-3xl font-bold text-orange-600">
                                    {violations.moderate}
                                </h4>
                            </div>
                            <div className="flex flex-col items-center rounded-lg bg-yellow-50 p-4 shadow-sm">
                                <InfoCircleOutlined className="mb-2 text-3xl text-yellow-700" />
                                <h3 className="mb-2 text-lg font-medium text-yellow-700">Minor</h3>
                                <h4 className="text-3xl font-bold text-yellow-600">
                                    {violations.minor}
                                </h4>
                            </div>
                        </div>
                        {report.videos.length > 0 && (
                            <div className="mt-4 text-center text-sm text-gray-600">
                                <ExclamationCircleOutlined className="mr-1 inline" />
                                This site has videos please make sure they are properly tagged with{' '}
                                <code>role=&quot;video&quot;</code> and <code>aria-label</code>{' '}
                                attributes.{' '}
                                <a
                                    href={'https://dequeuniversity.com/rules/axe/4.7/video-caption'}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                >
                                    Learn more
                                </a>
                            </div>
                        )}
                    </section>
                    <section className="mt-6">
                        <Card
                            title={
                                <span className="text-2xl font-semibold">
                                    How to read the Report
                                </span>
                            }
                        >
                            <p className="mb-4 text-base text-gray-700">
                                This report provides an automated assessment of your webpage’s
                                accessibility, highlighting issues that may affect users with
                                disabilities. Each issue is classified by severity to help you
                                prioritize fixes:
                            </p>
                            <ul className="mb-6">
                                <li className="flex items-start mb-2">
                                    <ExclamationCircleOutlined className="mt-1 mr-2 text-red-600" />
                                    <span>
                                        <strong>Critical:</strong> Major barriers that prevent
                                        access for many users. Immediate attention required.
                                    </span>
                                </li>
                                <li className="flex items-start mb-2">
                                    <AlertOutlined className="mt-1 mr-2 text-red-500" />
                                    <span>
                                        <strong>Serious:</strong> Significant issues that can make
                                        content difficult to use. Should be fixed promptly.
                                    </span>
                                </li>
                                <li className="flex items-start mb-2">
                                    <WarningOutlined className="mt-1 mr-2 text-orange-500" />
                                    <span>
                                        <strong>Moderate:</strong> Problems that may inconvenience
                                        some users but do not block access.
                                    </span>
                                </li>
                                <li className="flex items-start mb-2">
                                    <InfoCircleOutlined className="mt-1 mr-2 text-yellow-500" />
                                    <span>
                                        <strong>Minor:</strong> Low-impact issues that may affect
                                        usability in specific cases.
                                    </span>
                                </li>
                            </ul>
                            <p className="mb-2 text-base text-gray-700">
                                The{' '}
                                <strong>
                                    <a href="#website-preview">Website Preview</a>
                                </strong>{' '}
                                section shows your page with accessibility overlays, helping you
                                visually identify problem areas. For the most accurate results, use
                                the provided
                                <a href="#report-injection-script"> injection script</a> or the{' '}
                                <a href="https://chromewebstore.google.com/detail/axe-devtools-web-accessib/lhdoppojpmngadmnindnejefpokejbdd">
                                    Chrome extension
                                </a>{' '}
                                to highlight issues directly on your live site.
                            </p>
                            <p className="mb-2 text-base text-gray-700">
                                The{' '}
                                <strong>
                                    <a href="#report-photo">Report Photo</a>
                                </strong>{' '}
                                captures the state of your webpage at the time of the scan,
                                including detected accessibility issues. Use this to compare with
                                the live site and ensure consistency.
                            </p>
                            <p className="mb-2 text-base text-gray-700">
                                If you notice differences between the preview and your live site,
                                run the injection script in your browser’s DevTools Console to
                                render this report on the page. This could be due to dynamic content
                                or changes made after the initial scan.
                            </p>
                            <p className="mt-4 text-base text-gray-700">
                                At the{' '}
                                <a href="#detailed-accessibility-issues">bottom of this page</a>,
                                you’ll find a detailed list of all detected accessibility issues.
                                Each entry includes guidance and context to help you resolve them
                                and improve your site’s inclusivity.
                            </p>
                        </Card>
                    </section>
                </Card>
            </Content>
            <Content className="mb-2">
                <Card>
                    <h1 className="mb-4 text-2xl font-semibold">Website Preview</h1>
                    <div
                        className="mb-4 rounded-lg border max-h-[700px] overflow-auto w-full hover:shadow-lg transition-shadow relative"
                        id="website-preview"
                    >
                        <div className="right-1 top-0 p-2 absolute">
                            <Console
                                label="Accessibility Report Script"
                                command={`var accessScriptElement = document.createElement('script');
accessScriptElement.src = '${report_script_full_url}';
document.body.appendChild(accessScriptElement);`}
                                mini
                            />
                        </div>
                        <Suspense
                            fallback={
                                <div className="h-[500px] flex items-center justify-center">
                                    <PageLoading />
                                </div>
                            }
                        >
                            <SiteIframe
                                url={'/proxy?url=' + report.url + '&reportId=' + report.id}
                            />
                        </Suspense>
                    </div>
                    <div>
                        <h2 className="mb-4 text-2xl font-semibold">Inject Script</h2>
                        <p className="mb-2">
                            To highlight accessibility issues on the webpage, go to the webpage and
                            copy and paste the script below into your browser&apos;s{' '}
                            <a
                                href="https://developer.chrome.com/docs/devtools/console/"
                                target="_blank"
                                rel="noopener noreferrer"
                            >
                                DevTools Console
                            </a>
                            .<br />
                            <span className="block mt-1 text-gray-500 text-sm">
                                Tip: Open DevTools with <kbd>Ctrl</kbd> + <kbd>Shift</kbd> +{' '}
                                <kbd>K</kbd> (or <kbd>F12</kbd>), then go to the Console tab. You
                                may have to type{' '}
                                <span className="font-semibold">allow pasting</span> into the
                                console.
                            </span>
                        </p>
                    </div>
                    <Console
                        id="report-injection-script"
                        label="Accessibility Report Script"
                        command={`var accessScriptElement = document.createElement('script');
accessScriptElement.src = '${report_script_full_url}';
document.body.appendChild(accessScriptElement);`}
                    />
                </Card>
                <div className="mt-2">
                    <Card>
                        <h2 className="my-4 text-2xl font-semibold">Report Photo</h2>
                        <Tooltip title="This is a screenshot of the page at the time of the report, including any detected accessibility issues.">
                            <div className="max-h-[300px] overflow-auto" id="report-photo">
                                <Image
                                    src={report_photo_url}
                                    alt="Report Photo"
                                    preview
                                    className="rounded-lg w-full hover:shadow-lg transition-shadow"
                                />
                            </div>
                        </Tooltip>
                    </Card>
                </div>

                {report.report.violations.length > 0 && (
                    <div className="mt-2">
                        <Card>
                            <div>
                                <h2
                                    className="mb-4 text-2xl font-semibold"
                                    id="detailed-accessibility-issues"
                                >
                                    Accessibility Issues
                                </h2>
                                <p className="mb-2">
                                    The following accessibility issues were found on the page:
                                </p>
                            </div>
                            <div className="mt-4">
                                {report.report.violations.map((violation, index) => (
                                    <AuditAccessibilityItem
                                        key={index}
                                        accessibilityResult={violation}
                                    />
                                ))}
                            </div>
                        </Card>
                    </div>
                )}
                <div className="mt-4">
                    <Card>
                        <h2 className="mb-4 text-2xl font-semibold">Questions</h2>
                        <p className="mb-2">
                            Need help interpreting this report, fixing accessibility issues, or
                            requesting a rescan? Our team is here to support you. Reach out anytime
                            at{' '}
                            <a
                                href="mailto:a11y@cs.rutgers.edu"
                                className="text-blue-600 underline hover:text-blue-800"
                            >
                                a11y@cs.rutgers.edu
                            </a>
                            .
                        </p>
                    </Card>
                </div>
            </Content>

            {/* <pre>{JSON.stringify(report, null, 2)}</pre> */}
        </Content>
    );
}

export default Report;

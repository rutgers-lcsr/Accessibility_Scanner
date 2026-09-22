import Console from '@/components/Console';
import { Report as ReportType } from '@/lib/types/axe';
import { ExclamationCircleOutlined } from '@/lib/icons';

import AdminReportItems from '@/app/reports/[reportId]/components/AdminReportItems';
import ImpactTiles from '@/components/ImpactTiles';
import PageError from '@/components/PageError';
import PageLoading from '@/components/PageLoading';
import ViolationsList from '@/components/ViolationsList';
import { User } from '@/lib/types/user';
import { Alert, Card, Flex, Image, Space, Tooltip } from 'antd';
import { Content } from 'antd/es/layout/layout';
import { getCurrentUser } from 'next-cas-client/app';
import { Suspense } from 'react';
import HeaderLink from './components/HeaderLink';
import PageIframe from './components/PageIframe';
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

async function Report({ params }: { params: Promise<{ reportId: string }> }) {
    const { reportId } = await params;
    const user = await getCurrentUser<User>();

    const report = await getReport(reportId);
    if (typeof report === 'string') return <PageError title={report} status={403} />;
    if (report === null) return <PageError status={404} />;
    if (!report) return <PageError status={404} />;

    const violations = report.report_counts.violations;

    // Built from configuration, not the request's Host header, which a client controls.
    const report_script_full_url = `${process.env.NEXT_PUBLIC_BASE_URL}/api/reports/script/${report.script_token}/`;

    const report_photo_url = `/api/reports/${reportId}/photo/`;

    return (
        <>
            <Content className="mb-8 p-4">
                <Space direction="vertical" size="large" style={{ width: '100%' }}>
                    <Card>
                        <h2 className="mb-2 text-3xl font-extrabold">
                            Report for <HeaderLink url={report.url} />
                        </h2>

                        <ReportDate dateString={report.timestamp} />
                        <h3 className="mb-4 text-lg text-gray-500">Website: {report.base_url}</h3>

                        <section
                            aria-labelledby="accessibility-report"
                            className="rounded-lg bg-gray-50 p-6"
                        >
                            <Flex justify="space-between" className="mb-4">
                                <h2
                                    id="accessibility-report"
                                    className="mb-6 text-2xl font-semibold text-gray-800"
                                >
                                    Accessibility Report
                                </h2>
                                <div>
                                    <Tooltip title="Download Full Report as PDF">
                                        <a
                                            href={`/api/reports/${report.id}/pdf/`}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="rounded bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                                        >
                                            Download PDF
                                        </a>
                                    </Tooltip>
                                </div>
                            </Flex>

                            <ImpactTiles counts={violations} />
                            {report.videos.length > 0 && (
                                <div className="mt-4 text-center text-sm text-gray-600">
                                    <ExclamationCircleOutlined className="mr-1 inline" />
                                    This url has videos please make sure they are properly tagged
                                    with <code>role=&quot;video&quot;</code> and{' '}
                                    <code>aria-label</code> attributes.{' '}
                                    <a
                                        href={
                                            'https://dequeuniversity.com/rules/axe/4.7/video-caption'
                                        }
                                        target="_blank"
                                        rel="noopener noreferrer"
                                    >
                                        Learn more
                                    </a>
                                </div>
                            )}
                        </section>
                        <section className="mt-6 mb-6">
                            <Card
                                title={
                                    <span className="text-2xl font-semibold">
                                        How to read the Report
                                    </span>
                                }
                            >
                                <p className="mb-2 text-base text-gray-700">
                                    The{' '}
                                    <strong>
                                        <a href="#url-preview">Url Preview</a>
                                    </strong>{' '}
                                    gives you more information about each error, but may not show
                                    them all.
                                </p>
                                <p className="mb-2 text-base text-gray-700">
                                    The{' '}
                                    <strong>
                                        <a href="#report-photo">Report Photo</a>
                                    </strong>{' '}
                                    shows all the errors reported, but without explanations or
                                    context.
                                </p>
                                <div className="mb-2 text-base text-gray-700">
                                    To display all errors with explainations either use the{' '}
                                    <ul>
                                        <li className="list-disc ml-6">
                                            Use the{' '}
                                            <a href="#report-injection-script">injection script</a>
                                        </li>
                                        <li className="list-disc ml-6">
                                            Install The following{' '}
                                            <a href="https://chromewebstore.google.com/detail/axe-devtools-web-accessib/lhdoppojpmngadmnindnejefpokejbdd">
                                                Chrome extension
                                            </a>{' '}
                                            or{' '}
                                            <a href="https://addons.mozilla.org/en-US/firefox/addon/axe-devtools/">
                                                Firefox extension
                                            </a>
                                        </li>
                                    </ul>{' '}
                                </div>
                                <p className="mt-4 text-base text-gray-700">
                                    At the{' '}
                                    <a
                                        href="#detailed-accessibility-issues"
                                        className="font-bold hover:underline text-blue-800"
                                    >
                                        bottom of this page
                                    </a>
                                    , you’ll find a detailed list of all detected accessibility
                                    issues and links to resources for <b>fixing them</b>.
                                </p>
                            </Card>
                        </section>
                        {user?.is_admin && <AdminReportItems report={report} />}
                    </Card>

                    <Card>
                        <h1 className="mb-4 text-2xl font-semibold">Url Preview</h1>

                        <div
                            className="mb-4 rounded-lg border max-h-[700px] overflow-auto w-full hover:shadow-lg transition-shadow relative"
                            id="url-preview"
                        >
                            <Suspense
                                fallback={
                                    <div className="h-[500px] flex items-center justify-center">
                                        <PageLoading />
                                    </div>
                                }
                            >
                                <PageIframe
                                    url={`/proxy?report=${report.id}&url=${encodeURIComponent(report.url)}`}
                                >
                                    <Console
                                        label="Accessibility Report Script"
                                        command={`var accessScriptElement = document.createElement('script');
accessScriptElement.src = '${report_script_full_url}';
document.body.appendChild(accessScriptElement);`}
                                        mini
                                    />
                                </PageIframe>
                            </Suspense>
                        </div>
                        <a href="#report-injection-script">
                            <Alert
                                message="Note: This is a preview of the page. Some elements may not display correctly. All accessibility issues found are listed in the Report Photo and Detailed Accessibility Issues sections below."
                                type="info"
                                showIcon
                                className="m-4"
                            />
                        </a>

                        <div>
                            <h2 className="mb-4 text-2xl font-semibold">Inject Script</h2>
                            <p className="mb-2">
                                To highlight accessibility issues on the webpage, go to the webpage
                                and copy and paste the script below into your browser&apos;s{' '}
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
                                    <kbd>K</kbd> (or <kbd>F12</kbd>), then go to the Console tab.
                                    You may have to type{' '}
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
                    <Card>
                        <h2 className="my-4 text-2xl font-semibold">Report Photo</h2>
                        <Tooltip title="This is a screenshot of the page at the time of the report, including any detected accessibility issues.">
                            <div className="max-h-[400px] overflow-auto" id="report-photo">
                                <Image
                                    src={report_photo_url}
                                    alt="Report Photo"
                                    preview
                                    className="rounded-lg w-full hover:shadow-lg transition-shadow"
                                />
                            </div>
                        </Tooltip>
                    </Card>

                    {report.report.violations.length > 0 && (
                        <Card>
                            <h2
                                className="mb-4 text-2xl font-semibold"
                                id="detailed-accessibility-issues"
                            >
                                Accessibility Issues
                            </h2>
                            <p className="mb-2">
                                The following accessibility issues were found on the page:
                            </p>
                            <div className="mt-4">
                                <ViolationsList
                                    violations={report.report.violations}
                                    url={report.url}
                                    previewEnabled
                                    findings={report.findings}
                                    canEdit={report.can_edit}
                                />
                            </div>
                        </Card>
                    )}
                </Space>
            </Content>
        </>
    );
}

export default Report;

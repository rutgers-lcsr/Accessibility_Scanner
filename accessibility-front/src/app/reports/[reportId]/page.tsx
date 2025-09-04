import Console from '@/components/Console';
import { Report as ReportType } from '@/lib/types/axe';
import {
    AlertOutlined,
    ExclamationCircleOutlined,
    InfoCircleOutlined,
    WarningOutlined,
} from '@ant-design/icons';
import { Content } from 'antd/es/layout/layout';
import { format } from 'date-fns';
import { headers } from 'next/headers';

import AdminReportItems from '@/components/AdminReportItems';
import AuditAccessibilityItem from '@/components/AuditAccessibilityItem';
import PageError from '@/components/PageError';
import { User } from '@/lib/types/user';
import { Card, Image } from 'antd';
import { getCurrentUser } from 'next-cas-client/app';
import HeaderLink from './components/HeaderLink';
import SiteIframe from './components/SiteIframe';

interface Props {
    reportId: string;
}

// The reason this is a server component and the rest of them are not, is that all of them should have been really :0
export const getReport = async (reportId: string) => {
    const headerList = await headers();
    // need to forward the request as if we are the user
    // Theres an isssue with headers for some reason out of out control. the type is messed up

    const user = await getCurrentUser<User>()

    const options = {
        headers: user && {
            'Authorization': `Bearer ${user.access_token || ''}`
        }
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
                        {report?.timestamp
                            ? format(new Date(report.timestamp), 'MMMM dd, yyyy')
                            : 'N/A'}
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
                                <p className="text-3xl font-bold text-red-600">
                                    {violations.critical}
                                </p>
                            </div>
                            <div className="flex flex-col items-center rounded-lg bg-red-100 p-4 shadow-sm">
                                <AlertOutlined className="mb-2 text-3xl text-red-700" />
                                <h3 className="mb-2 text-lg font-medium text-red-700">Serious</h3>
                                <p className="text-3xl font-bold text-red-600">
                                    {violations.serious}
                                </p>
                            </div>
                            <div className="flex flex-col items-center rounded-lg bg-orange-50 p-4 shadow-sm">
                                <WarningOutlined className="mb-2 text-3xl text-orange-700" />
                                <h3 className="mb-2 text-lg font-medium text-orange-700">
                                    Moderate
                                </h3>
                                <p className="text-3xl font-bold text-orange-600">
                                    {violations.moderate}
                                </p>
                            </div>
                            <div className="flex flex-col items-center rounded-lg bg-yellow-50 p-4 shadow-sm">
                                <InfoCircleOutlined className="mb-2 text-3xl text-yellow-700" />
                                <h3 className="mb-2 text-lg font-medium text-yellow-700">Minor</h3>
                                <p className="text-3xl font-bold text-yellow-600">
                                    {violations.minor}
                                </p>
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
                </Card>
            </Content>
            <Content className="mb-2">
                <Card>
                    <div className="mb-4 max-h-[300px] overflow-auto">
                        <Image src={report_photo_url} alt="Report Photo" className="rounded-lg" />
                    </div>
                    <div className="mb-4 rounded-lg bg-blue-50 p-4">
                       <SiteIframe url={report.url} />
                    </div>

                    <div>
                        <h2 className="mb-4 text-2xl font-semibold">Inject Script</h2>
                        <p className="mb-2">
                            To view the accessibility issues directly on the webpage, inject the
                            following script into the browser devtools <a href="https://developer.chrome.com/docs/devtools/console/" target="_blank" rel="noopener noreferrer">console</a> while on the page you want to
                            audit:
                        </p>
                    </div>
                    <Console
                        label="Accessibility Report Script"
                        command={`var accessScriptElement = document.createElement('script');
accessScriptElement.src = '${report_script_full_url}';
document.body.appendChild(accessScriptElement);`}
                    />
                </Card>

                <div className="mt-2">
                    <Card>
                        <div>
                            <h2 className="mb-4 text-2xl font-semibold">Accessibility Issues</h2>
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
            </Content>

            {/* <pre>{JSON.stringify(report, null, 2)}</pre> */}
        </Content>
    );
}

export default Report;

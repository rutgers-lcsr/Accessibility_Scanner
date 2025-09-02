import { fetcherApi } from '@/lib/api';
import { Report as ReportType } from '@/lib/types/axe';
import { User } from '@/lib/types/user';
import { useUser } from '@/providers/User';
import {
    AlertOutlined,
    ExclamationCircleOutlined,
    InfoCircleOutlined,
    WarningOutlined,
} from '@ant-design/icons';
import { Image } from 'antd';
import { Content } from 'antd/es/layout/layout';
import { format } from 'date-fns';
import useSWR from 'swr';
import AdminReportItems from './AdminReportItems';
import AuditAccessibilityItem from './AuditAccessibilityItem';
import Console from './Console';
import PageError from './PageError';
import PageLoading from './PageLoading';

type Props = {
    report_id: string;
    user: User | null;
};


function Report({ report_id,user }: Props) {
    const { handlerUserApiRequest } = useUser();

    const {
        data: reportData,
        error,
        isLoading,
    } = useSWR(
        `/api/reports/${report_id}`,
        user ? handlerUserApiRequest<ReportType> : fetcherApi<ReportType>
    );

    if (isLoading) return <PageLoading />;
    if (error) return <PageError status={500} title="Error loading report" />;
    if (!reportData) return <PageError status={404} />;

    const violations = reportData.report_counts.violations;

    const report_script_full_url = `/api/reports/${report_id}/script`;

    const report_photo_url = `/api/reports/${report_id}/photo`;

    return (
        <Content className="">
            <header className="mb-8">
                <h1 className="mb-2 text-3xl font-extrabold">
                    Report for{' '}
                    <span
                        onClick={() => window.open(reportData.url)}
                        className="cursor-pointer text-blue-700 underline"
                    >
                        {reportData.url}
                    </span>
                </h1>
                {user && user.is_admin && <AdminReportItems report={reportData} />}
                <h2 className="mb-2 text-lg text-gray-500">
                    Report Date:{' '}
                    {reportData?.timestamp
                        ? format(new Date(reportData.timestamp), 'MMMM dd, yyyy')
                        : 'N/A'}
                </h2>
                <h3 className="mb-4 text-lg text-gray-500">Website: {reportData.base_url}</h3>
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
                            <p className="text-3xl font-bold text-red-600">{violations.critical}</p>
                        </div>
                        <div className="flex flex-col items-center rounded-lg bg-red-100 p-4 shadow-sm">
                            <AlertOutlined className="mb-2 text-3xl text-red-700" />
                            <h3 className="mb-2 text-lg font-medium text-red-700">Serious</h3>
                            <p className="text-3xl font-bold text-red-600">{violations.serious}</p>
                        </div>
                        <div className="flex flex-col items-center rounded-lg bg-orange-50 p-4 shadow-sm">
                            <WarningOutlined className="mb-2 text-3xl text-orange-700" />
                            <h3 className="mb-2 text-lg font-medium text-orange-700">Moderate</h3>
                            <p className="text-3xl font-bold text-orange-600">
                                {violations.moderate}
                            </p>
                        </div>
                        <div className="flex flex-col items-center rounded-lg bg-yellow-50 p-4 shadow-sm">
                            <InfoCircleOutlined className="mb-2 text-3xl text-yellow-700" />
                            <h3 className="mb-2 text-lg font-medium text-yellow-700">Minor</h3>
                            <p className="text-3xl font-bold text-yellow-600">{violations.minor}</p>
                        </div>
                    </div>
                    {reportData.videos.length > 0 && (
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
            </header>
            <Content className="mb-8">
                <div className="mb-4 max-h-[300px] overflow-auto">
                    <Image src={report_photo_url} alt="Report Photo" className="rounded-lg" />
                </div>

                <div>
                    <h2 className="mb-4 text-2xl font-semibold">Inject Script</h2>
                    <p className="mb-2">
                        To view the accessibility issues directly on the webpage, inject the
                        following script into the browser console while on the page you want to
                        audit:
                    </p>
                </div>
                <Console
                    label="Accessibility Report Script"
                    command={`var accessScriptElement = document.createElement('script');
accessScriptElement.src = '${report_script_full_url}';
document.body.appendChild(accessScriptElement);
                `}
                />

                <div className="mt-8">
                    <div>
                        <h2 className="mb-4 text-2xl font-semibold">Accessibility Issues</h2>
                        <p className="mb-2">
                            The following accessibility issues were found on the page:
                        </p>
                    </div>
                    <div className="mt-4">
                        {reportData.report.violations.map((violation, index) => (
                            <AuditAccessibilityItem key={index} accessibilityResult={violation} />
                        ))}
                    </div>
                </div>
            </Content>

            {/* <pre>{JSON.stringify(reportData, null, 2)}</pre> */}
        </Content>
    );
}

export default Report;

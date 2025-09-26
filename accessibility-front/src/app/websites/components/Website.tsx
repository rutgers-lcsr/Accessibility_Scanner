'use client';
import HeaderLink from '@/app/reports/[reportId]/components/HeaderLink';
import PageHeading from '@/components/PageHeading';
import { fetcherApi } from '@/lib/api';
import { User } from '@/lib/types/user';
import { Website as WebsiteType } from '@/lib/types/website';
import { useUser } from '@/providers/User';
import {
    AlertOutlined,
    ExclamationCircleOutlined,
    InfoCircleOutlined,
    WarningOutlined,
} from '@ant-design/icons';
import { Alert, Layout, Tabs, TabsProps, Tooltip } from 'antd';
import useSWR from 'swr';
import PageError from '../../../components/PageError';
import PageLoading from '../../../components/PageLoading';
import AdminItems from './AdminItems';
import WebsiteAdminItems from './WebsiteAdminItems';
import WebsiteReport from './WebsiteReport';
import WebsiteSiteTable from './WebsiteSiteTable';
const { Content } = Layout;

type Props = {
    websiteId: number;
    user: User | null;
};

const Website = ({ websiteId, user }: Props) => {
    const { handlerUserApiRequest } = useUser();

    const {
        data: websiteReport,
        error: reportError,
        isLoading: isLoadingReport,
        mutate: mutateWebsiteReport,
    } = useSWR(
        `/api/websites/${websiteId}`,
        user ? handlerUserApiRequest<WebsiteType> : fetcherApi<WebsiteType>
    );

    if (reportError) return <PageError status={500} title="Error loading website report" />;
    if (!websiteReport) return <PageLoading />;

    const violations = websiteReport.report_counts.violations;

    // Mutate both the website report and the sites data when it become stale,
    // this is needed for a full page reload when the website is scanned
    const mutate = async (website?: WebsiteType) => {
        mutateWebsiteReport(website);
    };

    const WebsiteReportItems: TabsProps['items'] = [
        {
            key: '1',
            label: `Urls (${websiteReport.sites.length})`,
            children: (
                <>
                    {isLoadingReport ? (
                        <PageLoading />
                    ) : reportError ? (
                        <PageError status={500} title="Error loading website report" />
                    ) : (
                        <WebsiteSiteTable websiteId={websiteId} user={user} />
                    )}
                </>
            ),
        },
        {
            key: '2',
            label: `Violations (${violations.total})`,
            children: <WebsiteReport report={websiteReport.report} />,
        },
    ];

    const isUserPartOfUsers =
        user &&
        (websiteReport.users.some((u) => u === user.user) || websiteReport.admin === user.user) &&
        !user.is_admin;

    return (
        <>
            <PageHeading title="Website Report" />
            <Content className="mb-8 p-4">
                <h2 className="mb-10 text-3xl font-extrabold">
                    Website Report for <HeaderLink url={`${websiteReport.url}`} />
                </h2>

                {user && user.is_admin && <AdminItems website={websiteReport} mutate={mutate} />}
                {/** Admin items for the website For Regular Users Usually the Owner of the site */}
                {isUserPartOfUsers ||
                    (process.env['NODE_ENV'] === 'development' && (
                        <WebsiteAdminItems website={websiteReport} mutate={mutate} />
                    ))}
                <h2 className="mb-4 text-lg text-gray-500">
                    Last Scanned:{' '}
                    {websiteReport?.last_scanned
                        ? new Date(websiteReport.last_scanned).toLocaleString()
                        : 'Never'}
                </h2>
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
                            <Tooltip
                                title="Major barriers that prevent
                                        access for many users. Immediate attention required."
                            >
                                <ExclamationCircleOutlined className="mb-2 text-3xl text-red-700" />
                                <h3 className="mb-2 text-lg font-medium text-red-700">Critical</h3>
                                <h4 className="text-3xl font-bold text-red-600">
                                    {violations.critical}
                                </h4>
                            </Tooltip>
                        </div>
                        <div className="flex flex-col items-center rounded-lg bg-red-100 p-4 shadow-sm">
                            <Tooltip
                                title="Significant issues that can make
                                        content difficult to use. Should be fixed promptly."
                            >
                                <AlertOutlined className="mb-2 text-3xl text-red-700" />
                                <h3 className="mb-2 text-lg font-medium text-red-700">Serious</h3>
                                <h4 className="text-3xl font-bold text-red-600">
                                    {violations.serious}
                                </h4>
                            </Tooltip>
                        </div>
                        <div className="flex flex-col items-center rounded-lg bg-orange-50 p-4 shadow-sm">
                            <Tooltip
                                title="Problems that may inconvenience
                                        some users but do not block access."
                            >
                                <WarningOutlined className="mb-2 text-3xl text-orange-700" />
                                <h3 className="mb-2 text-lg font-medium text-orange-700">
                                    Moderate
                                </h3>
                                <h4 className="text-3xl font-bold text-orange-600">
                                    {violations.moderate}
                                </h4>
                            </Tooltip>
                        </div>
                        <div className="flex flex-col items-center rounded-lg bg-yellow-50 p-4 shadow-sm">
                            <Tooltip
                                title="Low-impact issues that may
                                        affect usability in specific cases."
                            >
                                <InfoCircleOutlined className="mb-2 text-3xl text-yellow-700" />
                                <h3 className="mb-2 text-lg font-medium text-yellow-700">Minor</h3>
                                <h4 className="text-3xl font-bold text-yellow-600">
                                    {violations.minor}
                                </h4>
                            </Tooltip>
                        </div>
                    </div>
                    {violations.total > 15 && (
                        // Give some advice if there are too many violations
                        <div className="mt-6 rounded-md p-4">
                            <Alert
                                message="Consider prioritizing the most critical issues first to make the biggest impact on your websites accessibility. Take a look a the violations tab to get started. This will show you a list of common issues and how to fix them."
                                type="info"
                                style={{}}
                                showIcon
                            />
                        </div>
                    )}
                </section>

                <section aria-labelledby="website-report">
                    <Tabs defaultActiveKey="1" items={WebsiteReportItems} />
                </section>
            </Content>
        </>
    );
};

export default Website;

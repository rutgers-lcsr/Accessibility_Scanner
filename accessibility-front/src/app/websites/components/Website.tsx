'use client';
import HeaderLink from '@/app/reports/[reportId]/components/HeaderLink';
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
import { Tabs, TabsProps } from 'antd';
import { format } from 'date-fns';
import React from 'react';
import useSWR from 'swr';
import PageError from '../../../components/PageError';
import PageLoading from '../../../components/PageLoading';
import AdminWebsiteItems from './AdminWebsiteItems';
import WebsiteReport from './WebsiteReport';
import WebsiteSiteTable from './WebsiteSiteTable';

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
    // Use a ref to avoid resetting pageSize on re-render
    const [currentPage, setCurrentPage] = React.useState(1);
    const [pageSize, setPageSize] = React.useState(10);
    React.useEffect(() => {
        setPageSize(pageSize);
    }, [pageSize]);

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
            label: `Sites (${websiteReport.sites.length})`,
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
            label: `Voilations (${violations.total})`,
            children: <WebsiteReport report={websiteReport.report} />,
        },
    ];

    return (
        <div>
            <header className="mb-8">
                <h1 className="mb-2 text-3xl font-extrabold">
                    Website Report for <HeaderLink url={`${websiteReport.url}`} />
                </h1>
                {user && user.is_admin && (
                    <AdminWebsiteItems website={websiteReport} mutate={mutate} />
                )}
                <h2 className="mb-4 text-lg text-gray-500">
                    Last Scanned:{' '}
                    {websiteReport?.last_scanned
                        ? format(websiteReport?.last_scanned, 'MMMM dd, yyyy HH:mm:ss z')
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
                </section>
            </header>

            <section aria-labelledby="website-report">
                <Tabs defaultActiveKey="1" items={WebsiteReportItems} />
            </section>
        </div>
    );
};

export default Website;

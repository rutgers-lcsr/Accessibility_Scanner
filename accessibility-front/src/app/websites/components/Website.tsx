'use client';
import HeaderLink from '@/app/reports/[reportId]/components/HeaderLink';
import ImpactTiles from '@/components/ImpactTiles';
import PageHeading from '@/components/PageHeading';
import { fetcherApi } from '@/lib/api';
import { PublicUser } from '@/lib/types/user';
import { Website as WebsiteType } from '@/lib/types/website';
import { useUrlFilters } from '@/lib/urlFilters';
import { useUser } from '@/providers/User';
import { Alert, Layout, Tabs, TabsProps } from 'antd';
import useSWR from 'swr';
import PageError from '../../../components/PageError';
import PageLoading from '../../../components/PageLoading';
import AdminItems from './AdminItems';
import FixFirst from './FixFirst';
import NotificationToggle from './NotificationToggle';
import WebsiteAdminItems from './WebsiteAdminItems';
import WebsiteChanges from './WebsiteChanges';
import WebsiteDocumentsTable from './WebsiteDocumentsTable';
import WebsiteHistoryChart from './WebsiteHistoryChart';
import WebsiteReport from './WebsiteReport';
import WebsiteSiteTable from './WebsiteSiteTable';
const { Content } = Layout;

type Props = {
    websiteId: number;
    user: PublicUser | null;
};

const Website = ({ websiteId, user }: Props) => {
    const { handlerUserApiRequest } = useUser();
    // The open tab lives in the URL (?tab=) so links from emails and cards land on it.
    const { params, setFilters } = useUrlFilters();
    const activeTab = params.get('tab') ?? 'fix';

    const {
        data: websiteReport,
        error: reportError,
        isLoading: isLoadingReport,
        mutate: mutateWebsiteReport,
    } = useSWR(
        `/api/websites/${websiteId}`,
        user ? handlerUserApiRequest<WebsiteType> : fetcherApi<WebsiteType>
    );
    if (isLoadingReport) return <PageLoading />;
    if (!websiteReport || reportError)
        return <PageError status={500} title="Error loading website report" />;

    const violations = websiteReport.report_counts.violations;
    // Site admins, the website's admin and its members triage (Website.can_edit).
    const canEdit =
        !!user &&
        (user.is_admin ||
            websiteReport.admin === user.user ||
            websiteReport.users.includes(user.user));

    // Mutate both the website report and the sites data when it become stale,
    // this is needed for a full page reload when the website is scanned
    const mutate = async (website?: WebsiteType) => {
        mutateWebsiteReport(website);
    };

    const WebsiteReportItems: TabsProps['items'] = [
        {
            key: 'fix',
            label: 'Fix first',
            children: (
                <FixFirst
                    websiteId={websiteId}
                    user={user}
                    canEdit={canEdit}
                    categories={websiteReport.categories}
                    onCountsChanged={() => mutateWebsiteReport()}
                />
            ),
        },
        {
            key: 'urls',
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
            key: 'violations',
            label: `Violations (${violations.total})`,
            children: (
                <WebsiteReport
                    websiteId={websiteId}
                    report={websiteReport.report}
                    user={user}
                    canEdit={canEdit}
                    onCountsChanged={() => mutateWebsiteReport()}
                />
            ),
        },
        {
            key: 'history',
            label: 'History',
            children: <WebsiteHistoryChart websiteId={websiteId} user={user} />,
        },
        {
            key: 'changes',
            label: 'What changed',
            children: <WebsiteChanges websiteId={websiteId} user={user} />,
        },
        {
            key: 'documents',
            label: `Documents (${websiteReport.documents?.total ?? 0})`,
            children: (
                <>
                    {(websiteReport.documents?.untagged_pdf ?? 0) > 0 && (
                        <Alert
                            className="mt-2 mb-4"
                            type="warning"
                            showIcon
                            message={`${websiteReport.documents.untagged_pdf} untagged PDF${websiteReport.documents.untagged_pdf === 1 ? '' : 's'}`}
                            description="Untagged PDFs have no reading structure, so screen readers cannot navigate them. Re-export them with tagging enabled or replace them with web pages."
                        />
                    )}
                    <WebsiteDocumentsTable websiteId={websiteId} user={user} />
                </>
            ),
        },
    ];

    // console.log(websiteReport);
    // console.log(user);

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
                {isUserPartOfUsers && <WebsiteAdminItems website={websiteReport} mutate={mutate} />}
                {user && <NotificationToggle website={websiteReport} user={user} />}
                <h2 className="mb-4 text-lg text-gray-500">
                    Last Scanned:{' '}
                    {websiteReport?.last_scanned
                        ? new Date(websiteReport.last_scanned).toLocaleString()
                        : 'Never'}
                </h2>
                {websiteReport.last_scan_status &&
                    websiteReport.last_scan_status !== 'completed' && (
                        <Alert
                            className="mb-6"
                            type="error"
                            showIcon
                            message={
                                websiteReport.last_scan_status === 'unreachable'
                                    ? 'The last scan could not reach this website'
                                    : 'The last scan failed'
                            }
                            description={websiteReport.last_scan_error || undefined}
                        />
                    )}
                <section
                    aria-labelledby="accessibility-report"
                    className="rounded-lg bg-gray-50 p-6"
                >
                    <h2
                        id="accessibility-report"
                        className="mb-6 text-2xl font-semibold text-gray-800"
                    >
                        Accessibility Report
                    </h2>
                    <ImpactTiles counts={violations} />
                    {violations.total > 15 && (
                        // Give some advice if there are too many violations
                        <div className="mt-6 rounded-md p-4">
                            <Alert
                                message="Start with the Fix first tab: it ranks the issues by how many pages one fix clears, and links to a guide for each."
                                type="info"
                                style={{}}
                                showIcon
                            />
                        </div>
                    )}
                </section>

                <section aria-labelledby="website-report">
                    <Tabs
                        activeKey={activeTab}
                        onChange={(key) => setFilters({ tab: key === 'fix' ? null : key })}
                        items={WebsiteReportItems}
                    />
                </section>
            </Content>
        </>
    );
};

export default Website;

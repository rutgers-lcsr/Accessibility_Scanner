'use client';
import Content from '@/components/Content';
import HeaderLink from '@/app/reports/[reportId]/components/HeaderLink';
import ImpactTiles from '@/components/ImpactTiles';
import PageHeading from '@/components/PageHeading';
import PolicyNote from '@/components/PolicyNote';
import { fetcherApi } from '@/lib/api';
import { AxeReportCounts } from '@/lib/types/axe';
import { WebsiteFixFirst } from '@/lib/types/finding';
import { PublicUser } from '@/lib/types/user';
import { Website as WebsiteType } from '@/lib/types/website';
import { useUrlFilters } from '@/lib/urlFilters';
import { useUser } from '@/providers/User';
import { Alert, Segmented, Tabs, TabsProps } from 'antd';
import Link from 'next/link';
import { useEffect } from 'react';
import useSWR, { useSWRConfig } from 'swr';
import PageError from '../../../components/PageError';
import PageLoading from '../../../components/PageLoading';
import AdminItems from './AdminItems';
import FixFirst from './FixFirst';
import NotificationToggle from './NotificationToggle';
import ScanWebsiteButton from './ScanWebsiteButton';
import WebsiteAdminItems from './WebsiteAdminItems';
import WebsiteChanges from './WebsiteChanges';
import WebsiteDocumentsTable from './WebsiteDocumentsTable';
import WebsiteCompliance from './WebsiteCompliance';
import WebsiteContent from './WebsiteContent';
import WebsiteHealth from './WebsiteHealth';
import WebsiteMedia from './WebsiteMedia';
import WebsiteThirdParties from './WebsiteThirdParties';
import WebsiteHistoryChart from './WebsiteHistoryChart';
import WebsiteLinksTable from './WebsiteLinksTable';
import WebsiteReport from './WebsiteReport';
import WebsiteSiteTable from './WebsiteSiteTable';

// "12 days ago (Sep 28, 2026)". Rendered only in the browser (this page waits for its
// data on the client), so the age and the local date cannot mismatch the server.
function scanAge(iso: string | null | undefined): string {
    if (!iso) return 'never';
    const date = new Date(iso);
    const days = Math.floor((Date.now() - date.getTime()) / 86_400_000);
    const age = days < 1 ? 'today' : days === 1 ? 'yesterday' : `${days} days ago`;
    return `${age} (${date.toLocaleDateString(undefined, { dateStyle: 'medium' })})`;
}

// Open elements per severity from the Fix first ranking (suppressed rules excluded).
function elementCounts(data: WebsiteFixFirst): AxeReportCounts {
    const counts: AxeReportCounts = { total: 0, critical: 0, serious: 0, moderate: 0, minor: 0 };
    for (const rule of data.rules) {
        counts.total += rule.elements;
        if (rule.impact) counts[rule.impact] += rule.elements;
    }
    return counts;
}

const isStale = (iso: string | null | undefined) =>
    !!iso && Date.now() - new Date(iso).getTime() > 30 * 86_400_000;

// Old tab keys and the group they now belong to.
const TAB_ALIASES: Record<string, string> = {
    changes: 'history',
    documents: 'links',
    media: 'inventory',
    'third-parties': 'inventory',
    content: 'inventory',
    health: 'inventory',
};

type Props = {
    websiteId: number;
    user: PublicUser | null;
};

const Website = ({ websiteId, user }: Props) => {
    const { handlerUserApiRequest } = useUser();
    const { mutate: mutateAll } = useSWRConfig();
    // The open tab lives in the URL (?tab=) so links from emails and cards land on it.
    const { params, setFilters } = useUrlFilters();
    // Tabs were grouped (13 → 8); the old keys in emails and links open the group.
    const requestedTab = params.get('tab') ?? 'fix';
    const activeTab = TAB_ALIASES[requestedTab] ?? requestedTab;
    const section = params.get('section');

    // ?tab=changes and ?tab=documents land on a section further down: go there once the
    // tab has rendered.
    useEffect(() => {
        const target =
            requestedTab === 'changes'
                ? 'what-changed'
                : requestedTab === 'documents'
                  ? 'documents'
                  : null;
        if (!target) return;
        // The section loads its own data, so look for it for a few seconds.
        let tries = 0;
        const timer = window.setInterval(() => {
            const el = document.getElementById(target);
            if (el && el.offsetHeight > 40) {
                el.scrollIntoView({ block: 'start' });
                window.clearInterval(timer);
            } else if (++tries > 30) {
                window.clearInterval(timer);
            }
        }, 200);
        return () => window.clearInterval(timer);
    }, [requestedTab]);

    const {
        data: websiteReport,
        error: reportError,
        isLoading: isLoadingReport,
        mutate: mutateWebsiteReport,
    } = useSWR(
        `/api/websites/${websiteId}`,
        user ? handlerUserApiRequest<WebsiteType> : fetcherApi<WebsiteType>
    );
    // The tiles count open elements, the unit Fix first ranks by, so the two agree.
    // Same key as FixFirst, so SWR makes one request for both.
    const { data: fixFirst } = useSWR(
        `/api/websites/${websiteId}/fix-first`,
        user ? handlerUserApiRequest<WebsiteFixFirst> : fetcherApi<WebsiteFixFirst>
    );
    if (isLoadingReport) return <PageLoading />;
    if (!websiteReport || reportError)
        return <PageError status={500} title="Error loading website report" />;

    const violations = websiteReport.report_counts.violations;
    const openCounts = fixFirst ? elementCounts(fixFirst) : null;
    const toCheck = websiteReport.report.incomplete?.length ?? 0;
    // Site admins, the website's admin and its members triage (Website.can_edit).
    const canEdit =
        !!user &&
        (user.is_admin ||
            websiteReport.admin === user.user ||
            websiteReport.users.includes(user.user));
    // Same people may rescan a page (Website.can_scan).
    const canScan = canEdit;
    // A page rescan changes the counts, the pages table and every list: refresh them all.
    const onPageScanned = () =>
        mutateAll((key) => typeof key === 'string' && key.startsWith(`/api/websites/${websiteId}`));

    // Mutate both the website report and the sites data when it become stale,
    // this is needed for a full page reload when the website is scanned
    const mutate = async (website?: WebsiteType) => {
        mutateWebsiteReport(website);
    };

    // A heading per tab panel, for screen-reader users moving by headings.
    const panelHeading = (text: string) => <h2 className="sr-only">{text}</h2>;
    const plural = (n: number, noun: string) => `${n} ${noun}${n === 1 ? '' : 's'}`;

    // Inventory: the crawl inventories, one tab with a switch, so the tab bar stays short.
    const inventoryOptions = [
        { value: 'media', label: `Media (${websiteReport.media_counts?.total ?? 0})` },
        {
            value: 'third-parties',
            label: `Third parties (${websiteReport.third_party_count ?? 0})`,
        },
        {
            value: 'content',
            label: websiteReport.content_counts?.stale_pages
                ? `Content (${websiteReport.content_counts.stale_pages} stale)`
                : 'Content',
        },
        { value: 'health', label: 'Health' },
    ];
    const inventorySection = inventoryOptions.some((o) => o.value === section)
        ? section
        : inventoryOptions.some((o) => o.value === requestedTab)
          ? requestedTab
          : 'media';
    const stalePages = websiteReport.content_counts?.stale_pages ?? 0;

    const WebsiteReportItems: TabsProps['items'] = [
        {
            key: 'fix',
            label: 'Fix first',
            children: (
                <>
                    {panelHeading('Fix first')}
                    <FixFirst
                        websiteId={websiteId}
                        user={user}
                        canEdit={canEdit}
                        categories={websiteReport.categories}
                        onCountsChanged={() => mutateWebsiteReport()}
                        canScan={canScan}
                        onPageScanned={onPageScanned}
                    />
                </>
            ),
        },
        {
            key: 'urls',
            label: `Pages (${websiteReport.sites.length})`,
            children: (
                <>
                    {panelHeading('Pages')}
                    <WebsiteSiteTable
                        websiteId={websiteId}
                        user={user}
                        canScan={canScan}
                        onPageScanned={onPageScanned}
                    />
                </>
            ),
        },
        {
            key: 'violations',
            // Distinct failing rules: the tiles count elements, so this count names its unit.
            label: `By rule (${websiteReport.report.violations?.length ?? 0})`,
            children: (
                <WebsiteReport
                    websiteId={websiteId}
                    report={websiteReport.report}
                    user={user}
                    canEdit={canEdit}
                    onCountsChanged={() => mutateWebsiteReport()}
                    canScan={canScan}
                    onPageScanned={onPageScanned}
                />
            ),
        },
        {
            // The trend, then what the latest scans changed (?tab=changes lands here).
            key: 'history',
            label: 'History',
            children: (
                <>
                    {panelHeading('History')}
                    <WebsiteHistoryChart websiteId={websiteId} user={user} />
                    <div id="what-changed" style={{ marginTop: 16 }}>
                        <WebsiteChanges websiteId={websiteId} user={user} />
                    </div>
                </>
            ),
        },
        {
            // ?tab=documents and ?tab=links land here.
            key: 'links',
            label: 'Links & documents',
            children: (
                <>
                    <h2 className="text-lg font-semibold" style={{ margin: '8px 0 12px' }}>
                        Links ({websiteReport.link_counts?.total ?? 0})
                    </h2>
                    {(websiteReport.link_counts?.broken ?? 0) > 0 && (
                        <Alert
                            style={{ marginBottom: 16 }}
                            type="warning"
                            showIcon
                            title={plural(websiteReport.link_counts.broken, 'broken link')}
                            description="These links lead to a page that no longer exists. Fix or remove them on the pages listed under Linked from."
                        />
                    )}
                    <WebsiteLinksTable websiteId={websiteId} user={user} />
                    <h2
                        id="documents"
                        className="text-lg font-semibold"
                        style={{ margin: '32px 0 12px' }}
                    >
                        Documents ({websiteReport.documents?.total ?? 0})
                    </h2>
                    {(websiteReport.documents?.untagged_pdf ?? 0) > 0 && (
                        <Alert
                            style={{ marginBottom: 16 }}
                            type="warning"
                            showIcon
                            title={plural(websiteReport.documents.untagged_pdf, 'untagged PDF')}
                            description="Untagged PDFs have no reading structure, so screen readers cannot navigate them. Re-export them with tagging enabled or replace them with web pages."
                        />
                    )}
                    <WebsiteDocumentsTable websiteId={websiteId} user={user} />
                </>
            ),
        },
        {
            // ?tab=media, third-parties, content and health land here, on that section.
            key: 'inventory',
            label: stalePages ? `Inventory (${stalePages} stale)` : 'Inventory',
            children: (
                <>
                    {panelHeading('Inventory')}
                    <Segmented
                        value={inventorySection}
                        onChange={(value) =>
                            setFilters({ tab: 'inventory', section: String(value) })
                        }
                        options={inventoryOptions}
                        aria-label="Inventory section"
                        style={{ margin: '8px 0 16px' }}
                    />
                    {inventorySection === 'media' && (
                        <WebsiteMedia
                            websiteId={websiteId}
                            user={user}
                            canEdit={canEdit}
                            onChanged={() => mutateWebsiteReport()}
                        />
                    )}
                    {inventorySection === 'third-parties' && (
                        <WebsiteThirdParties websiteId={websiteId} user={user} />
                    )}
                    {inventorySection === 'content' && (
                        <WebsiteContent websiteId={websiteId} user={user} />
                    )}
                    {inventorySection === 'health' && (
                        <WebsiteHealth websiteId={websiteId} user={user} canEdit={canEdit} />
                    )}
                </>
            ),
        },
    ];

    // Deadlines, exceptions and manual reviews: for signed-in people who can see the website.
    if (user) {
        const overdue = websiteReport.compliance?.overdue ?? 0;
        WebsiteReportItems.push({
            key: 'compliance',
            label: overdue ? `Compliance (${overdue} overdue)` : 'Compliance',
            children: (
                <WebsiteCompliance
                    website={websiteReport}
                    user={user}
                    canEdit={canEdit}
                    onChanged={() => mutateWebsiteReport()}
                />
            ),
        });
    }

    // Settings come after the results: the people who can change them (site admins, the
    // website's admin and its members) open this tab, everyone lands on Fix first.
    if (user && canEdit) {
        WebsiteReportItems.push({
            key: 'settings',
            label: 'Settings',
            children: (
                <div className="space-y-4">
                    <NotificationToggle website={websiteReport} user={user} />
                    {user.is_admin ? (
                        <AdminItems website={websiteReport} mutate={mutate} />
                    ) : (
                        <WebsiteAdminItems website={websiteReport} mutate={mutate} />
                    )}
                </div>
            ),
        });
    }
    // A ?tab= this user has no tab for (Settings for a viewer) falls back to Fix first.
    const shownTab = WebsiteReportItems.some((item) => item.key === activeTab) ? activeTab : 'fix';

    return (
        <>
            <PageHeading
                title={
                    <>
                        Website Report for <HeaderLink url={`${websiteReport.url}`} />
                    </>
                }
                subtitle={
                    <>
                        Last full scan {scanAge(websiteReport.last_scanned)}
                        {!!websiteReport.page_rescans?.count && (
                            <>
                                {' '}
                                · {plural(websiteReport.page_rescans.count, 'page')} rescanned
                                since, latest{' '}
                                {new Date(websiteReport.page_rescans.latest!).toLocaleDateString(
                                    undefined,
                                    {
                                        dateStyle: 'medium',
                                    }
                                )}
                            </>
                        )}
                        {isStale(websiteReport.last_scanned) && (
                            <span className="font-medium text-orange-800">
                                {' '}
                                · over a month old
                                {canEdit
                                    ? ': if the site has changed since, scan it again before relying on these results'
                                    : ''}
                            </span>
                        )}
                    </>
                }
                actions={
                    canEdit && (
                        <ScanWebsiteButton websiteId={websiteId} onComplete={() => mutate()} />
                    )
                }
            />
            <Content className="mb-8 p-4">
                {websiteReport.last_scan_status &&
                    websiteReport.last_scan_status !== 'completed' && (
                        <Alert
                            style={{ marginBottom: 24 }}
                            type="error"
                            showIcon
                            title={
                                websiteReport.last_scan_status === 'unreachable'
                                    ? 'The last scan could not reach this website'
                                    : 'The last scan failed'
                            }
                            description={websiteReport.last_scan_error || undefined}
                        />
                    )}
                <section aria-labelledby="accessibility-report" className="mb-2">
                    <h2 id="accessibility-report" className="sr-only">
                        Summary
                    </h2>
                    {openCounts ? (
                        <ImpactTiles
                            counts={openCounts}
                            listId="issues-by-rule"
                            query="tab=violations"
                        />
                    ) : (
                        <ImpactTiles counts={violations} />
                    )}
                    <p
                        className="max-w-[75ch] text-sm text-gray-700"
                        // Inline: antd's unlayered reset beats Tailwind margins on <p>.
                        style={{ margin: '16px 0 0' }}
                    >
                        {openCounts
                            ? `${plural(openCounts.total, 'open issue')} across the website, by severity. Each issue is one element on a page that fails a check.`
                            : "Failing checks across the website's pages, by severity."}
                        {(fixFirst?.suppressed_elements ?? 0) > 0 && (
                            // Nothing leaves the counts unannounced.
                            <>
                                {' '}
                                {plural(fixFirst?.suppressed_elements ?? 0, 'more element')} marked
                                false positive or accepted{' '}
                                {fixFirst?.suppressed_elements === 1 ? 'is' : 'are'} not counted.
                            </>
                        )}
                        {toCheck > 0 && (
                            <>
                                {' '}
                                <Link href="?tab=violations#needs-review">
                                    {toCheck} more rule{toCheck === 1 ? '' : 's'} need a manual
                                    check
                                </Link>
                                .
                            </>
                        )}
                    </p>
                    <PolicyNote />
                </section>

                <section aria-label="Report details">
                    <Tabs
                        activeKey={shownTab}
                        onChange={(key) =>
                            setFilters({ tab: key === 'fix' ? null : key, section: null })
                        }
                        items={WebsiteReportItems}
                    />
                </section>
            </Content>
        </>
    );
};

export default Website;

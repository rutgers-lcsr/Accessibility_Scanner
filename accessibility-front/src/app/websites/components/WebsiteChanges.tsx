'use client';
import PageError from '@/components/PageError';
import PageLoading from '@/components/PageLoading';
import { fetcherApi } from '@/lib/api';
import { WebsiteChanges as WebsiteChangesType } from '@/lib/types/finding';
import { PublicUser } from '@/lib/types/user';
import { useUser } from '@/providers/User';
import { Alert, Card, Collapse } from 'antd';
import useSWR from 'swr';
import RuleRows from './RuleRows';

type Props = {
    websiteId: number;
    user: PublicUser | null;
};

// New, fixed and still-open findings between the previous and the latest scan.
function WebsiteChanges({ websiteId, user }: Props) {
    const { handlerUserApiRequest } = useUser();
    const { data, error, isLoading } = useSWR<WebsiteChangesType>(
        `/api/websites/${websiteId}/changes`,
        user ? handlerUserApiRequest<WebsiteChangesType> : fetcherApi<WebsiteChangesType>
    );

    if (isLoading) return <PageLoading />;
    if (error || !data) return <PageError status={500} title="Could not load the changes" />;

    const when = (value: string | null) => (value ? new Date(value).toLocaleString() : 'n/a');

    if (!data.since) {
        return (
            <Card style={{ marginTop: 8 }} title="What changed">
                <Alert
                    type="info"
                    showIcon
                    title="Only one scan so far"
                    description="Once this website has been scanned again, this tab shows what is new, what was fixed and what is still open."
                />
            </Card>
        );
    }

    const nothing = data.new_count === 0 && data.fixed_count === 0;

    return (
        <Card style={{ marginTop: 8 }} title="What changed">
            <p className="mb-4">
                {/* Two units, each named: rule failures for the before/after totals (a
                    rule failing on one page counts once), elements for what changed. */}
                Each page&apos;s two most recent scans, the latest on {when(data.until)}:{' '}
                <strong>{data.previous.total}</strong> → <strong>{data.current.total}</strong> rule
                failures on the pages scanned both times. Elements:{' '}
                <strong>{data.new_count}</strong> new
                {data.reopened_count > 0 && <> ({data.reopened_count} reopened)</>},{' '}
                <strong>{data.fixed_count}</strong> fixed, <strong>{data.open_count}</strong> still
                open
                {data.suppressed_count > 0 && (
                    <>, {data.suppressed_count} marked false positive or accepted</>
                )}
                .
            </p>
            {data.regression && (
                <Alert
                    style={{ marginBottom: 16 }}
                    type="warning"
                    showIcon
                    title="This scan is worse than the previous one"
                />
            )}
            {nothing && (
                <Alert
                    style={{ marginBottom: 16 }}
                    type="success"
                    showIcon
                    title="Nothing changed"
                />
            )}
            <Collapse
                defaultActiveKey={['new', 'fixed']}
                items={[
                    {
                        key: 'new',
                        label: `New (${data.new_count})`,
                        children: <RuleRows rules={data.new} empty="No new violations." />,
                    },
                    {
                        key: 'fixed',
                        label: `Fixed (${data.fixed_count})`,
                        children: (
                            <RuleRows
                                rules={data.fixed}
                                empty="Nothing was fixed since the previous scan."
                            />
                        ),
                    },
                    {
                        key: 'open',
                        label: `Still open (${data.still_open.reduce((n, r) => n + r.count, 0)})`,
                        children: (
                            <RuleRows rules={data.still_open} empty="Nothing carried over." />
                        ),
                    },
                ]}
            />
        </Card>
    );
}

export default WebsiteChanges;

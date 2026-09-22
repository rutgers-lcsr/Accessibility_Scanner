'use client';
import ImpactTiles from '@/components/ImpactTiles';
import PageLoading from '@/components/PageLoading';
import ViolationsList from '@/components/ViolationsList';
import { APIError } from '@/lib/api';
import { QuickScanResponse, isQuickScanResult } from '@/lib/types/scan';
import { useUser } from '@/providers/User';
import { Alert, Card, Image, Tag } from 'antd';
import Link from 'next/link';
import useSWR from 'swr';

type Props = {
    taskId: string;
};

// The outcome of one quick scan: counts, screenshot and the violations, read from the
// result endpoint (polled while the task is still running).
function QuickScanResult({ taskId }: Props) {
    const { handlerUserApiRequest } = useUser();
    const { data, error, isLoading } = useSWR<QuickScanResponse>(
        `/api/scans/quick/${taskId}`,
        handlerUserApiRequest<QuickScanResponse>,
        {
            refreshInterval: (latest) =>
                latest && !isQuickScanResult(latest) && !latest.error ? 2000 : 0,
        }
    );

    if (isLoading) return <PageLoading />;
    if (error) {
        const status = (error as APIError).response?.status;
        return (
            <Alert
                type={status === 410 ? 'warning' : 'error'}
                showIcon
                message={
                    status === 410
                        ? 'This quick scan result has expired'
                        : status === 404
                          ? 'No such quick scan'
                          : 'Could not load the quick scan'
                }
                description={
                    status === 410
                        ? 'Results are kept for a day. Run the scan again.'
                        : (error as Error).message
                }
            />
        );
    }
    if (!data) return null;

    if (!isQuickScanResult(data)) {
        if (data.error) {
            return (
                <Alert type="error" showIcon message="The scan failed" description={data.error} />
            );
        }
        return (
            <Card>
                <PageLoading />
                <div className="text-center text-gray-600">
                    {data.status || 'Waiting for a worker…'}
                </div>
            </Card>
        );
    }

    if (data.status === 'failed') {
        return (
            <Alert
                type="error"
                showIcon
                message={`Could not audit ${data.url}`}
                description={[data.error, data.response_code ? `HTTP ${data.response_code}` : null]
                    .filter(Boolean)
                    .join('. ')}
            />
        );
    }

    const violations = data.report?.violations ?? [];
    const truncated = violations.some((rule) => rule.nodes_truncated > 0);

    return (
        <div className="flex flex-col gap-6">
            <Card>
                <div className="mb-4 flex flex-wrap items-center gap-2">
                    <h2 className="text-2xl font-semibold">
                        <a href={data.url} target="_blank" rel="noopener noreferrer">
                            {data.url}
                        </a>
                    </h2>
                    {data.timestamp && <Tag>{new Date(data.timestamp).toLocaleString()}</Tag>}
                    {data.tabable === false && <Tag color="orange">Not keyboard navigable</Tag>}
                </div>
                {data.report_counts && <ImpactTiles counts={data.report_counts.violations} />}
                <div className="mt-4 text-sm text-gray-500">
                    This result is not stored and expires after a day. To track this page over time,{' '}
                    <Link href="/websites">add its website</Link>.
                </div>
            </Card>
            {data.photo_url ? (
                <Card title="Screenshot">
                    <div className="max-h-[400px] overflow-auto">
                        <Image
                            src={data.photo_url}
                            alt={`Screenshot of ${data.url} with violations highlighted`}
                            preview
                        />
                    </div>
                </Card>
            ) : (
                data.photo_omitted && (
                    <Alert type="info" showIcon message="The screenshot was too large to keep." />
                )
            )}
            <Card title={`Violations (${violations.length})`}>
                {truncated && (
                    <Alert
                        className="mb-4"
                        type="info"
                        showIcon
                        message="Only the first 50 elements of each rule are shown for a quick scan."
                    />
                )}
                {violations.length === 0 ? (
                    <div className="text-center text-green-600">
                        No accessibility violations found.
                    </div>
                ) : (
                    <ViolationsList violations={violations} url={data.url} />
                )}
            </Card>
        </div>
    );
}

export default QuickScanResult;

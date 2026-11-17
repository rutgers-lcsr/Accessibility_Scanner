'use client';
import PageError from '@/components/PageError';
import PageLoading from '@/components/PageLoading';
import { fetcherApi } from '@/lib/api';
import { CaptionStatus, MediaItem } from '@/lib/types/inventory';
import { Paged } from '@/lib/types/Paged';
import { PublicUser } from '@/lib/types/user';
import { useAlerts } from '@/providers/Alerts';
import { useUser } from '@/providers/User';
import { Alert, Pagination, Select, Table, Tag } from 'antd';
import React from 'react';
import useSWR from 'swr';

type Props = {
    websiteId: number;
    user: PublicUser | null;
    canEdit: boolean;
    onChanged: () => void;
};

const STATUS_TAG: Record<CaptionStatus, { color: string; label: string }> = {
    present: { color: 'green', label: 'Captions' },
    missing: { color: 'red', label: 'No captions' },
    unknown: { color: 'orange', label: 'Check by hand' },
};

const FILTERS: { value: CaptionStatus | 'all'; label: string }[] = [
    { value: 'all', label: 'All media' },
    { value: 'missing', label: 'No captions' },
    { value: 'unknown', label: 'Check by hand' },
    { value: 'present', label: 'Captions' },
];

// Videos, audio and embedded players on the website, captions first. The crawl can tell
// captions only for <video> with a <track>; people confirm the rest.
function WebsiteMedia({ websiteId, user, canEdit, onChanged }: Props) {
    const { handlerUserApiRequest } = useUser();
    const { addAlert } = useAlerts();
    const [page, setPage] = React.useState(1);
    const [pageSize, setPageSize] = React.useState(10);
    const [status, setStatus] = React.useState<CaptionStatus | 'all'>('all');
    const query = `page=${page}&limit=${pageSize}${status === 'all' ? '' : `&status=${status}`}`;
    const { data, error, isLoading, mutate } = useSWR(
        `/api/websites/${websiteId}/media/?${query}`,
        user ? handlerUserApiRequest<Paged<MediaItem>> : fetcherApi<Paged<MediaItem>>
    );

    const setVerdict = async (item: MediaItem, caption_override: MediaItem['caption_override']) => {
        try {
            await handlerUserApiRequest(`/api/websites/${websiteId}/media/${item.id}/`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ caption_override }),
            });
            await mutate();
            onChanged();
        } catch (e) {
            addAlert('Could not save: ' + (e as Error).message, 'error');
        }
    };

    if (error) return <PageError status={500} title="Error loading media" />;

    return (
        <>
            <Alert
                style={{ marginTop: 8, marginBottom: 16 }}
                type="info"
                showIcon
                title="Videos need captions, and audio needs a transcript."
                description="A <video> with a captions track is detected automatically. Embedded players (YouTube, Kaltura, Vimeo…) and audio can't be checked from the page, so open them and record what you find."
            />
            <div className="mb-3 flex items-center gap-2">
                <label htmlFor="media-filter">Show</label>
                <Select
                    id="media-filter"
                    style={{ width: 180 }}
                    value={status}
                    options={FILTERS}
                    onChange={(value) => {
                        setStatus(value);
                        setPage(1);
                    }}
                />
            </div>
            {!data ? (
                <PageLoading minimal />
            ) : (
                <>
                    <Table<MediaItem>
                        rowKey="id"
                        loading={isLoading}
                        pagination={false}
                        dataSource={data.items}
                        locale={{ emptyText: 'No media found on this website.' }}
                        columns={[
                            {
                                title: 'Media',
                                dataIndex: 'url',
                                key: 'url',
                                width: 380,
                                render: (url: string, item) => (
                                    <>
                                        <a
                                            href={url}
                                            target="_blank"
                                            rel="noreferrer"
                                            className="break-all"
                                        >
                                            {url}
                                        </a>
                                        <div className="text-xs text-gray-600">
                                            {item.kind}
                                            {item.provider &&
                                                item.provider !== 'html5' &&
                                                ` · ${item.provider}`}
                                            {item.audio_description && ' · audio description track'}
                                        </div>
                                    </>
                                ),
                            },
                            {
                                title: 'Captions',
                                key: 'status',
                                render: (_, item) => (
                                    <>
                                        <Tag color={STATUS_TAG[item.caption_status].color}>
                                            {STATUS_TAG[item.caption_status].label}
                                        </Tag>
                                        {item.override_by && (
                                            <div className="text-xs text-gray-600">
                                                confirmed by {item.override_by}
                                            </div>
                                        )}
                                    </>
                                ),
                            },
                            {
                                title: 'On pages',
                                dataIndex: 'pages',
                                key: 'pages',
                                width: 320,
                                render: (pages: string[]) => (
                                    <>
                                        {pages.slice(0, 3).map((page) => (
                                            <div key={page} className="break-all">
                                                {page}
                                            </div>
                                        ))}
                                        {pages.length > 3 && (
                                            <div className="text-xs text-gray-600">
                                                and {pages.length - 3} more
                                            </div>
                                        )}
                                    </>
                                ),
                            },
                            ...(canEdit
                                ? [
                                      {
                                          title: 'Your check',
                                          key: 'verdict',
                                          render: (_: unknown, item: MediaItem) => (
                                              <Select<string>
                                                  aria-label={`Caption check for ${item.url}`}
                                                  style={{ width: 170 }}
                                                  value={item.caption_override ?? 'none'}
                                                  onChange={(value) =>
                                                      setVerdict(
                                                          item,
                                                          value === 'none'
                                                              ? null
                                                              : (value as 'verified' | 'missing')
                                                      )
                                                  }
                                                  options={[
                                                      { value: 'none', label: 'Not checked' },
                                                      { value: 'verified', label: 'Has captions' },
                                                      { value: 'missing', label: 'No captions' },
                                                  ]}
                                              />
                                          ),
                                      },
                                  ]
                                : []),
                        ]}
                    />
                    <div className="flex justify-center py-4">
                        <Pagination
                            showSizeChanger
                            current={page}
                            pageSize={pageSize}
                            total={data.count}
                            onShowSizeChange={(_, size) => setPageSize(size)}
                            onChange={setPage}
                        />
                    </div>
                </>
            )}
        </>
    );
}

export default WebsiteMedia;

'use client';
/**
 * Extra start pages for a website's scans.
 *
 * Some websites do not link to every section from their root (a course site under a
 * personal GitHub Pages host, for example), so a crawl from the root never reaches them.
 * Each page listed here is crawled as another root of the website. The API rejects pages
 * that are not on the website's host.
 */
import { Website } from '@/lib/types/website';
import { useAlerts } from '@/providers/Alerts';
import { useUser } from '@/providers/User';
import { Select } from 'antd';
import { useState } from 'react';

type Props = {
    website: Website;
    mutate: (website?: Website) => Promise<void>;
};

function ExtraStartUrls({ website, mutate }: Props) {
    const { addAlert } = useAlerts();
    const { handlerUserApiRequest } = useUser();
    const [loading, setLoading] = useState(false);

    const handleChange = async (value: string[]) => {
        setLoading(true);
        try {
            const updatedWebsite = await handlerUserApiRequest<Website>(
                `/api/websites/${website.id}`,
                {
                    method: 'PATCH',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        extra_start_urls: value.map((v) => v.trim()).filter((v) => v !== ''),
                    }),
                }
            );
            mutate(updatedWebsite);
            addAlert('Start pages updated successfully', 'success');
        } catch (error) {
            addAlert('Failed to update start pages: ' + (error as Error).message, 'error');
        }
        setLoading(false);
    };

    return (
        <>
            <Select
                mode="tags"
                style={{ width: '100%' }}
                id="extra-start-urls"
                aria-label="Additional start pages"
                placeholder={`${website.url}/section/`}
                value={website.extra_start_urls ?? []}
                tokenSeparators={[',', ' ', '\n']}
                disabled={loading}
                onChange={handleChange}
            />
            <div className="mt-1 text-xs text-gray-500">
                Pages a scan starts from besides the website itself, for sections that are not
                linked from the root. Enter full URLs on this website, one per entry.
            </div>
        </>
    );
}

export default ExtraStartUrls;

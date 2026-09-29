'use client';
import { Tag } from 'antd';

type Props = {
    url: string;
    external: boolean;
    final_url: string | null;
};

// A link target as shown in both link tables: the URL, an off-site marker and, when the
// link redirected, where it ended up.
export function LinkCell({ url, external, final_url }: Props) {
    return (
        <>
            <a href={url} target="_blank" rel="noopener noreferrer" className="break-all">
                {url}
            </a>
            {external && (
                <Tag className="ml-2" bordered={false}>
                    off-site
                </Tag>
            )}
            {final_url && <div className="text-xs text-gray-500 break-all">Redirects to {final_url}</div>}
        </>
    );
}

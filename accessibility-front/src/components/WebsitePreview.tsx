'use client';
import { Image, Popover } from 'antd';
import { ReactNode, useState } from 'react';

type Props = {
    websiteId: number;
    url: string;
    children: ReactNode;
};

// A small screenshot of the website's home page, shown while the wrapped link is
// hovered or focused. The image is only requested once the popover first opens.
function WebsitePreview({ websiteId, url, children }: Props) {
    const [failed, setFailed] = useState(false);
    return (
        <Popover
            trigger={['hover', 'focus']}
            mouseEnterDelay={0.4}
            placement="rightTop"
            content={
                failed ? (
                    <div className="w-60 text-sm text-gray-500">
                        No screenshot of this website yet.
                    </div>
                ) : (
                    <Image
                        src={`/api/websites/${websiteId}/preview/`}
                        alt={`Screenshot of the home page of ${url}`}
                        width={480}
                        preview={false}
                        className="rounded"
                        style={{ maxWidth: '70vw', height: 'auto' }}
                        onError={() => setFailed(true)}
                    />
                )
            }
        >
            {children}
        </Popover>
    );
}

export default WebsitePreview;

'use client';

import { FullscreenExitOutlined, FullscreenOutlined, ReloadOutlined } from '@ant-design/icons';
import { Button, Tooltip } from 'antd';
import { ReactNode, useEffect, useRef, useState } from 'react';

type Props = {
    url: string;
    children?: ReactNode;
};

function PageIframe({ url, children }: Props) {
    const containerRef = useRef<HTMLDivElement>(null);
    const iframeRef = useRef<HTMLIFrameElement>(null);
    const [isFullscreen, setIsFullscreen] = useState(false);

    useEffect(() => {
        const onFullscreenChange = () =>
            setIsFullscreen(document.fullscreenElement === containerRef.current);
        document.addEventListener('fullscreenchange', onFullscreenChange);
        return () => document.removeEventListener('fullscreenchange', onFullscreenChange);
    }, []);

    const handleRefresh = () => {
        if (iframeRef.current) {
            // Re-assigning src reloads the iframe and returns it to the
            // original page even if the user navigated away inside it
            iframeRef.current.src = url;
        }
    };

    const toggleFullscreen = () => {
        if (document.fullscreenElement) {
            document.exitFullscreen();
        } else {
            containerRef.current?.requestFullscreen();
        }
    };

    return (
        <div ref={containerRef} className={`relative ${isFullscreen ? 'bg-white' : ''}`}>
            <div className="right-1 top-0 p-2 absolute z-10 flex gap-2">
                {children}
                <Tooltip title="Refresh preview">
                    <Button
                        icon={<ReloadOutlined />}
                        onClick={handleRefresh}
                        aria-label="Refresh page preview"
                    />
                </Tooltip>
                <Tooltip title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}>
                    <Button
                        icon={isFullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
                        onClick={toggleFullscreen}
                        aria-label={
                            isFullscreen ? 'Exit fullscreen preview' : 'Fullscreen page preview'
                        }
                    />
                </Tooltip>
            </div>
            <iframe
                onError={(e) => console.error('Iframe error:', e)}
                ref={iframeRef}
                src={url}
                title="Page Preview"
                className={isFullscreen ? 'w-full h-full' : 'w-full min-h-[700px]'}
                style={{ border: 'none' }}
                allow="*"
            />
        </div>
    );
}

export default PageIframe;

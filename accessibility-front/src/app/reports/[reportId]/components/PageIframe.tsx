'use client';

import { PREVIEW_FOCUS_EVENT } from '@/components/ViolationNode';
import { useAlerts } from '@/providers/Alerts';
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
    const [frameKey, setFrameKey] = useState(0);
    const { addAlert } = useAlerts();

    // "Show in preview" on a violation: scroll the framed page to the element and open
    // its tooltip. The frame is same-origin (/proxy), and the injected report script has
    // already tagged the element and defined .animation-highlight.
    useEffect(() => {
        const onFocus = (event: Event) => {
            const selector = (event as CustomEvent<{ selector?: string }>).detail?.selector;
            if (!selector) return;
            containerRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
            let target: Element | null = null;
            try {
                target = iframeRef.current?.contentDocument?.querySelector(selector) ?? null;
            } catch {
                target = null; // cross-origin frame or a selector the browser rejects
            }
            if (!target) {
                addAlert(
                    'Element not found in the preview; use the screenshot or the injection script',
                    'warning'
                );
                return;
            }
            target.scrollIntoView({ behavior: 'smooth', block: 'center' });
            target.classList.add('animation-highlight');
            target.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));
        };
        window.addEventListener(PREVIEW_FOCUS_EVENT, onFocus);
        return () => window.removeEventListener(PREVIEW_FOCUS_EVENT, onFocus);
    }, [addAlert]);

    useEffect(() => {
        const onFullscreenChange = () =>
            setIsFullscreen(document.fullscreenElement === containerRef.current);
        document.addEventListener('fullscreenchange', onFullscreenChange);
        return () => document.removeEventListener('fullscreenchange', onFullscreenChange);
    }, []);

    // A new iframe returns to the original page even if the user navigated away inside
    // it. Re-assigning src would not: the preview cancels navigations it did not start
    // from a click (previewGuard in lib/proxyRewrite).
    const handleRefresh = () => setFrameKey((key) => key + 1);

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
                key={frameKey}
                onError={(e) => console.error('Iframe error:', e)}
                ref={iframeRef}
                src={url}
                title="Page Preview"
                // Same origin, so "Show in preview" can reach into the frame, but a
                // frame-busting site cannot take the whole app with it.
                sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-modals"
                className={isFullscreen ? 'w-full h-full' : 'w-full min-h-[700px]'}
                style={{ border: 'none' }}
            />
        </div>
    );
}

export default PageIframe;

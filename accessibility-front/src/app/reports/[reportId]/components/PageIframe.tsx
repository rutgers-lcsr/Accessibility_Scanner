'use client';

import { PREVIEW_FOCUS_EVENT } from '@/components/ViolationNode';
import { FullscreenExitOutlined, FullscreenOutlined, ReloadOutlined } from '@ant-design/icons';
import { Button, Tooltip } from 'antd';
import { ReactNode, useEffect, useRef, useState } from 'react';

// Fired on window after "Show in preview": the element was or was not on the live page.
export const PREVIEW_FOUND_EVENT = 'a11y:preview-found';
export const PREVIEW_MISSING_EVENT = 'a11y:preview-missing';

type Props = {
    url: string;
    children?: ReactNode;
    // Size of the frame when not fullscreen; the report page puts it in a fixed-height panel.
    frameClassName?: string;
};

function PageIframe({ url, children, frameClassName = 'w-full min-h-[700px]' }: Props) {
    const containerRef = useRef<HTMLDivElement>(null);
    const iframeRef = useRef<HTMLIFrameElement>(null);
    const [isFullscreen, setIsFullscreen] = useState(false);
    const [frameKey, setFrameKey] = useState(0);
    // Where the reader was when they asked for "Show in preview": the issue list is far
    // above the preview, so offer the way back.
    const [returnTo, setReturnTo] = useState<number | null>(null);
    const returnFocus = useRef<HTMLElement | null>(null);

    // "Show in preview" on a violation: scroll the framed page to the element and open
    // its tooltip. The frame is same-origin (/proxy), and the injected report script has
    // already tagged the element and defined .animation-highlight.
    useEffect(() => {
        const onFocus = (event: Event) => {
            const selector = (event as CustomEvent<{ selector?: string }>).detail?.selector;
            if (!selector) return;
            // The button pressed, to give focus back to after "Back to the issue".
            returnFocus.current = document.activeElement as HTMLElement | null;
            // The panel holding the frame may only now be switching to it (PageViews), so
            // look for the element once it is visible.
            window.setTimeout(() => {
                const box = containerRef.current?.getBoundingClientRect();
                if (box) {
                    // Beside the issue list (wide screens) the list stays put: bring the
                    // preview into view only if needed, and no way back is needed.
                    const beside = box.left > window.innerWidth * 0.4;
                    if (beside) {
                        if (box.top < 0 || box.bottom > window.innerHeight)
                            containerRef.current?.scrollIntoView({
                                behavior: 'smooth',
                                block: 'nearest',
                            });
                    } else {
                        // Stacked below the list: go there and offer the way back.
                        setReturnTo(window.scrollY);
                        containerRef.current?.scrollIntoView({
                            behavior: 'smooth',
                            block: 'start',
                        });
                    }
                }
                let target: Element | null = null;
                try {
                    target = iframeRef.current?.contentDocument?.querySelector(selector) ?? null;
                } catch {
                    target = null; // cross-origin frame or a selector the browser rejects
                }
                if (!target) {
                    // Not on the page as it loads now: PageViews shows the screenshot instead.
                    window.dispatchEvent(
                        new CustomEvent(PREVIEW_MISSING_EVENT, { detail: { selector } })
                    );
                    return;
                }
                window.dispatchEvent(
                    new CustomEvent(PREVIEW_FOUND_EVENT, { detail: { selector } })
                );
                target.scrollIntoView({ behavior: 'smooth', block: 'center' });
                target.classList.add('animation-highlight');
                target.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));
            }, 50);
        };
        window.addEventListener(PREVIEW_FOCUS_EVENT, onFocus);
        return () => window.removeEventListener(PREVIEW_FOCUS_EVENT, onFocus);
    }, []);

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
        <div ref={containerRef} className={`relative h-full ${isFullscreen ? 'bg-white' : ''}`}>
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
            {returnTo !== null && !isFullscreen && (
                <div className="fixed bottom-6 left-1/2 z-20 -translate-x-1/2">
                    <Button
                        type="primary"
                        shape="round"
                        size="large"
                        onClick={() => {
                            window.scrollTo({ top: returnTo, behavior: 'smooth' });
                            setReturnTo(null);
                            returnFocus.current?.focus({ preventScroll: true });
                        }}
                    >
                        Back to the issue
                    </Button>
                </div>
            )}
            <iframe
                key={frameKey}
                onError={(e) => console.error('Iframe error:', e)}
                ref={iframeRef}
                src={url}
                title="Page Preview"
                // Same origin, so "Show in preview" can reach into the frame, but a
                // frame-busting site cannot take the whole app with it.
                sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-modals"
                className={isFullscreen ? 'w-full h-full' : frameClassName}
                style={{ border: 'none' }}
            />
        </div>
    );
}

export default PageIframe;

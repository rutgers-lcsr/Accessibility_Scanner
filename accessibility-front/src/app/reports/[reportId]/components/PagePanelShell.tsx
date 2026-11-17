'use client';

import { PREVIEW_FOCUS_EVENT } from '@/components/ViolationNode';
import { CloseOutlined } from '@ant-design/icons';
import { Button } from 'antd';
import { ReactNode, useEffect, useRef, useState } from 'react';

// Below the two-column width the page panel sits after the whole issue list, so on a phone
// "Show in preview" opened it as a bottom sheet over the list instead of scrolling screens
// away. The sheet takes focus, closes on Escape or its button, and gives focus back. The
// panel's content (and the live frame) is the same element either way, never mounted twice.
const NARROW = '(max-width: 1279px)';

export default function PagePanelShell({ children }: { children: ReactNode }) {
    const [sheet, setSheet] = useState(false);
    const closeRef = useRef<HTMLButtonElement>(null);
    const returnTo = useRef<HTMLElement | null>(null);

    const close = () => {
        setSheet(false);
        returnTo.current?.focus({ preventScroll: true });
    };

    useEffect(() => {
        const onShow = () => {
            if (!window.matchMedia(NARROW).matches) return;
            returnTo.current = document.activeElement as HTMLElement | null;
            setSheet(true);
        };
        window.addEventListener(PREVIEW_FOCUS_EVENT, onShow);
        return () => window.removeEventListener(PREVIEW_FOCUS_EVENT, onShow);
    }, []);

    useEffect(() => {
        if (!sheet) return;
        closeRef.current?.focus();
        const onKey = (event: KeyboardEvent) => {
            if (event.key === 'Escape') close();
        };
        window.addEventListener('keydown', onKey);
        return () => window.removeEventListener('keydown', onKey);
    });

    return (
        <>
            {sheet && (
                // The list behind stays visible but dimmed; a tap on it closes the sheet.
                <div
                    aria-hidden="true"
                    className="fixed inset-0 z-[1000] bg-black/30"
                    onClick={close}
                />
            )}
            <div
                data-sheet-open={sheet ? '' : undefined}
                role={sheet ? 'dialog' : undefined}
                aria-modal={sheet ? true : undefined}
                aria-label={sheet ? 'The page' : undefined}
                className={
                    sheet
                        ? 'fixed inset-x-0 bottom-0 z-[1001] max-h-[85vh] overflow-auto rounded-t-2xl bg-white p-3 shadow-2xl'
                        : ''
                }
            >
                {sheet && (
                    // Pinned: the preview scrolls the sheet to the element.
                    <div className="sticky top-0 z-10 -mx-3 -mt-3 mb-2 flex justify-end bg-white p-3">
                        <Button ref={closeRef} icon={<CloseOutlined />} onClick={close}>
                            Back to the list
                        </Button>
                    </div>
                )}
                {children}
            </div>
        </>
    );
}

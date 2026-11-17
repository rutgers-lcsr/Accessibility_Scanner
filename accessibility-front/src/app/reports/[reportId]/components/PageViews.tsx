'use client';

import Console from '@/components/Console';
import { PREVIEW_FOCUS_EVENT } from '@/components/ViolationNode';
import { Image, Segmented } from 'antd';
import { useEffect, useState } from 'react';
import PageIframe, { PREVIEW_FOUND_EVENT, PREVIEW_MISSING_EVENT } from './PageIframe';

type View = 'photo' | 'live';

type Props = {
    photoUrl: string;
    photoAlt: string;
    previewUrl: string;
    injectCommand: string;
    // After a redirect the screenshot is the faithful view, so it is the one shown first.
    redirected: boolean;
};

// The scanned page beside the issue list: the screenshot taken at scan time, or the page
// loaded live with the issues outlined. "Show in preview" on an element switches to the
// live view. Both stay mounted, so the live page has loaded by the time someone asks.
export default function PageViews({
    photoUrl,
    photoAlt,
    previewUrl,
    injectCommand,
    redirected,
}: Props) {
    const [view, setView] = useState<View>(redirected ? 'photo' : 'live');
    // Said to screen readers (and shown) after "Show in preview".
    const [status, setStatus] = useState('');

    useEffect(() => {
        const toLive = () => setView('live');
        const found = () => setStatus('Highlighted in the live preview.');
        // Not on the page as it loads now (it changed, or the scan was redirected): the
        // screenshot from the scan shows it, so switch to that rather than show nothing.
        const missing = () => {
            setView('photo');
            setStatus(
                'That element is not on the page as it loads now, so here is the screenshot from the scan, where it is outlined.'
            );
        };
        window.addEventListener(PREVIEW_FOCUS_EVENT, toLive);
        window.addEventListener(PREVIEW_FOUND_EVENT, found);
        window.addEventListener(PREVIEW_MISSING_EVENT, missing);
        return () => {
            window.removeEventListener(PREVIEW_FOCUS_EVENT, toLive);
            window.removeEventListener(PREVIEW_FOUND_EVENT, found);
            window.removeEventListener(PREVIEW_MISSING_EVENT, missing);
        };
    }, []);

    return (
        <div>
            <Segmented<View>
                block
                value={view}
                onChange={(next) => {
                    setView(next);
                    // Said, so a screen-reader user knows what the panel now holds.
                    setStatus(
                        next === 'photo'
                            ? 'Showing the screenshot from the scan.'
                            : 'Showing the live preview.'
                    );
                }}
                aria-label="How to show the page"
                options={[
                    { value: 'photo', label: 'Screenshot at scan time' },
                    { value: 'live', label: 'Live preview' },
                ]}
            />
            <output
                className="block text-sm font-medium text-gray-900"
                style={{ margin: status ? '12px 0 0' : 0 }}
            >
                {status}
            </output>
            <p className="text-sm text-gray-700" style={{ margin: '12px 0' }}>
                {view === 'photo'
                    ? 'The page exactly as it was scanned, with every issue found outlined.'
                    : 'The page as it loads now, with the issues outlined. Some elements may not display correctly here.'}
            </p>
            <div hidden={view !== 'photo'} id="report-photo">
                <div className="max-h-[70vh] overflow-auto rounded-lg border border-gray-200">
                    <Image src={photoUrl} alt={photoAlt} preview className="w-full" />
                </div>
            </div>
            <div hidden={view !== 'live'} id="url-preview">
                {/* The framed page is another site's, with its own links: let keyboard
                    users step over it. */}
                <a
                    href="#after-the-page"
                    className="sr-only focus:not-sr-only focus:mb-2 focus:inline-block"
                >
                    Skip the live preview
                </a>
                <div className="relative h-[70vh] min-h-[420px] w-full overflow-auto rounded-lg border border-gray-200">
                    <PageIframe url={previewUrl} frameClassName="w-full h-full">
                        <Console label="Accessibility Report Script" command={injectCommand} mini />
                    </PageIframe>
                </div>
            </div>
            <span id="after-the-page" tabIndex={-1} />
        </div>
    );
}

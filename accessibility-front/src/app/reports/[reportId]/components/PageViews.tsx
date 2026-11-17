'use client';

import Console from '@/components/Console';
import { PREVIEW_FOCUS_EVENT } from '@/components/ViolationNode';
import { Image, Segmented } from 'antd';
import { useEffect, useState } from 'react';
import PageIframe from './PageIframe';

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

    useEffect(() => {
        const toLive = () => setView('live');
        window.addEventListener(PREVIEW_FOCUS_EVENT, toLive);
        return () => window.removeEventListener(PREVIEW_FOCUS_EVENT, toLive);
    }, []);

    return (
        <div>
            <Segmented<View>
                block
                value={view}
                onChange={setView}
                aria-label="How to show the page"
                options={[
                    { value: 'photo', label: 'Screenshot at scan time' },
                    { value: 'live', label: 'Live preview' },
                ]}
            />
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
                <div className="relative h-[70vh] min-h-[420px] w-full overflow-auto rounded-lg border border-gray-200">
                    <PageIframe url={previewUrl} frameClassName="w-full h-full">
                        <Console label="Accessibility Report Script" command={injectCommand} mini />
                    </PageIframe>
                </div>
            </div>
        </div>
    );
}

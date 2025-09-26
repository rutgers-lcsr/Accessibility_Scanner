'use client';

// Functions related to browser detection and page size management

function getInitalPageSize(): PageSize {
    if (typeof window === 'undefined' || !window.localStorage) {
        return 5;
    }
    const saved = localStorage.getItem('websitePageSize');
    if (saved) {
        const parsed = parseInt(saved, 10);
        if (!isNaN(parsed) && parsed > 0) {
            if (pageSizeOptions.map(Number).includes(parsed)) {
                return parsed as PageSize;
            }
            return 5; // Default to 5 if not one of the expected values
        }
    }

    if (typeof window !== 'undefined') {
        const width = window.innerWidth;
        if (width < 600) return 5;
        if (width < 900) return 10;
        return 20;
    }
    return 5;
}

const pageSizeOptions = ['5', '10', '20', '50', '100'];
export type PageSize = 5 | 10 | 20 | 50 | 100;

/**
 * Axe Accessibility Tools Links
 */

// Links to axe accessibility tools for different browsers

const axeToolsLinks = {
    Chrome: 'https://chromewebstore.google.com/detail/axe-devtools-web-accessib/lhdoppojpmngadmnindnejefpokejbdd',
    Firefox: 'https://addons.mozilla.org/en-US/firefox/addon/axe-devtools/',
};

export type Browser = 'Chrome' | 'Firefox' | null;

function getAxeLink(browser: Browser = null): string {
    if (!browser) {
        browser = getCurrentBrowser(
            typeof window !== 'undefined' ? window.navigator.userAgent : undefined
        );
    }

    if (browser && axeToolsLinks[browser]) {
        return axeToolsLinks[browser as keyof typeof axeToolsLinks];
    }
    // Default to Chrome link if browser is not detected
    return axeToolsLinks.Chrome;
}

function getCurrentBrowser(userAgent: string | undefined): Browser {
    const isChrome = userAgent?.includes('Chrome');
    const isFirefox = userAgent?.includes('Firefox');

    if (isChrome) return 'Chrome';
    if (isFirefox) return 'Firefox';
    return null;
}

export { getAxeLink, getCurrentBrowser, getInitalPageSize, pageSizeOptions };

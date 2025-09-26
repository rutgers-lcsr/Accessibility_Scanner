const axeToolsLinks = {
    Chrome: 'https://chromewebstore.google.com/detail/axe-devtools-web-accessib/lhdoppojpmngadmnindnejefpokejbdd',
    Firefox: 'https://addons.mozilla.org/en-US/firefox/addon/axe-devtools/',
};

export type Browser = 'Chrome' | 'Firefox' | null;

function getAxeLink(browser: Browser = null): string {
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
export { getAxeLink, getCurrentBrowser };

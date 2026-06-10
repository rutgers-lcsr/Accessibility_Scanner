import asyncio
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError
from scanner.log import log_message

# JS that resolves once the DOM has stopped mutating for `quietMs`, or when the
# `maxMs` hard cap is reached. Catches React/SPA re-renders that happen after the
# network has gone idle.
_DOM_STABLE_JS = """
([quietMs, maxMs]) => new Promise((resolve) => {
    let timer;
    const done = () => { obs.disconnect(); resolve(true); };
    const obs = new MutationObserver(() => {
        clearTimeout(timer);
        timer = setTimeout(done, quietMs);
    });
    obs.observe(document.documentElement, {
        childList: true, subtree: true, attributes: true, characterData: true
    });
    timer = setTimeout(done, quietMs);  // settle if already quiet
    setTimeout(done, maxMs);            // hard cap
})
"""


async def wait_for_page_settled(
    page: Page,
    networkidle_timeout: int = 15000,
    dom_quiet_ms: int = 500,
    dom_timeout: int = 10000,
) -> bool:
    """
    Wait for a page (incl. React/SPA) to finish loading and rendering.

    1. Wait for network to go idle (no requests for ~500ms).
    2. Wait until the DOM stops mutating for `dom_quiet_ms` (MutationObserver).

    Each phase is bounded by its own timeout. On timeout we log a warning and
    return False (the caller still scans the current DOM). Returns True when the
    page settled cleanly.
    """
    settled = True

    try:
        await page.wait_for_load_state("networkidle", timeout=networkidle_timeout)
    except PlaywrightTimeoutError:
        log_message(
            f"Network did not go idle within {networkidle_timeout}ms for {page.url}, "
            "scanning current state",
            'warning',
        )
        settled = False

    try:
        # asyncio guard in case page.evaluate itself hangs past the JS hard cap.
        await asyncio.wait_for(
            page.evaluate(_DOM_STABLE_JS, [dom_quiet_ms, dom_timeout]),
            timeout=(dom_timeout / 1000) + 5,
        )
    except (asyncio.TimeoutError, PlaywrightTimeoutError):
        log_message(
            f"DOM did not stabilize within {dom_timeout}ms for {page.url}, "
            "scanning current state",
            'warning',
        )
        settled = False

    return settled

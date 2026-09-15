from playwright.async_api import Page

# Upper bound on Tab presses per page. Each press costs two round-trips to the browser,
# so the probe must stay cheap; a page with more focus stops than this is simply
# reported as tabbable.
MAX_TAB_PRESSES = 200


async def _get_current_focus(page: Page) -> dict | None:
    return await page.evaluate("""
            () => {
                const el = document.activeElement;
                if (!el) return null;
                return {
                    tag: el.tagName,
                    id: el.id,
                    class: el.className,
                    type: el.type || null,
                    name: el.name || null,
                    href: el.href || null,
                    text: (el.textContent || '').trim().slice(0, 80),
                };
            }
        """)


async def is_page_tabbable(page: Page) -> bool:
    """Press Tab and watch where focus goes.

    Not tabbable: focus does not move at all after the first press. Tabbable: focus moves
    and eventually cycles back to the first stop, or keeps moving for MAX_TAB_PRESSES.
    """
    await page.keyboard.press('Tab')
    begin_element = await _get_current_focus(page)
    for presses in range(1, MAX_TAB_PRESSES + 1):
        await page.keyboard.press('Tab')
        new_element = await _get_current_focus(page)
        if begin_element == new_element:
            return presses > 1
    return True

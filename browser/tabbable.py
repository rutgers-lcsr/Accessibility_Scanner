from playwright.async_api import Page


async def _get_current_focus(page: Page) -> str:
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
                    value: el.value || null,
                    html: el.innerHTML || null
                };
            }
        """)

timeout_count = 10000

async def is_page_tabbable(page:Page)-> bool:
    count = timeout_count
    await page.keyboard.press('Tab')
    begin_element = await _get_current_focus(page)
    while count > 0:
        count -= 1
        await page.keyboard.press('Tab')
        new_element = await _get_current_focus(page)
        if begin_element == new_element:
            # Assume that if tabbing happens between 2 counts and element is unchanged then we have a problem. 
            if(count > timeout_count - 2):
                return False
            return True

    return False
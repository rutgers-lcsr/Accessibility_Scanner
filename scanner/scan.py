import asyncio
from typing import List
from playwright.async_api import async_playwright
from browser.report import AccessibilityReport, generate_report
from log import log_message


async def process_website(name: int, browser, queue: asyncio.Queue, results: List[AccessibilityReport], sites_done: set[str], currently_processing: set[str]) -> AccessibilityReport:
    while True:
        website = await queue.get()
        if website is None:  # sentinel to shut down
            queue.task_done()
            break

        if website in currently_processing:
            queue.task_done()
            continue

        currently_processing.add(website)
        try:
            res = await generate_report(browser, website=website)
            

            if 'error' in res:
                log_message(f"[Worker {name}] Error for {website}: {res['error']}", 'error')
            else:
                for link in res.get('links', []):
                   if link not in sites_done and link not in currently_processing:
                       await queue.put(link)
            results.append(res)
            
            
            log_message(f"[Worker {name}] Processed {website}, websites left: {queue.qsize()}", 'info')
        
        finally:
            sites_done.add(website)
            currently_processing.remove(website)
            queue.task_done()


async def generate_reports(website: str = "https://resources.cs.rutgers.edu") -> List[AccessibilityReport]:
    results: List[AccessibilityReport] = []
    sites_done: set[str] = set()
    currently_processing: set[str] = set()


    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False,args=['--no-sandbox', '--disable-setuid-sandbox'])
        q = asyncio.Queue()
        await q.put(website)
        # Launch N workers
        num_workers = 10
        workers = [
            asyncio.create_task(process_website(i, browser, q, results,sites_done, currently_processing))
            for i in range(num_workers)
        ]

        # Wait until all items are processed
        await q.join()

        # Stop workers
        for _ in range(num_workers):
            await q.put(None)
        await asyncio.gather(*workers)

    return results


asyncio.run(generate_reports())
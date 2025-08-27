import asyncio
from typing import List
from playwright.async_api import async_playwright
from mail.emails import ScanFinishedEmail
from scanner.browser.report import AccessibilityReport, generate_report
from scanner.log import log_message
from app import create_app
from models import db
from models.website import Site, Website
from models.report import Report
from scanner.utils.queue import ListQueue
from scanner.utils.service import check_url
from utils.urls import get_full_url, get_netloc, get_site_netloc

sites_done: set[str] = set()
currently_processing: set[str] = set()


async def process_website(name: int, browser, queue: ListQueue, results: List[AccessibilityReport], sites_done: set[str], currently_processing: set[str]) -> AccessibilityReport:
    while True:
        site = await queue.get()
        if site is None:  # sentinel to shut down
            queue.task_done()
            break

        if site in currently_processing:
            queue.task_done()
            continue
        currently_processing.add(site)
        try:
            res = await generate_report(browser, website=site)
            

            if 'error' in res:
                log_message(f"[Worker {name}] Error for {site}: {res['error']}", 'error')
            else:
                # add links to queue if not already processing
                for site_link in res.get('links', []):
                    if not site_link in sites_done and not site_link in currently_processing and not queue.exists(site_link):
                        await queue.put(site_link)
                        
                                    
                results.append(res)
        finally:
            sites_done.add(site)
            currently_processing.remove(site)
            queue.task_done()
            log_message(f"[Worker {name}] Processed {site}, websites left: {queue.qsize()} currently processing: {len(currently_processing)} sites_done: {len(sites_done)}", 'info')


        

async def generate_single_site_report(site_url:str) -> AccessibilityReport:
    app = create_app()
    base_url = get_netloc(site_url)
    website_url = get_full_url(site_url)
    with app.app_context():
        site = Site.query.filter_by(url=website_url).first()
        if site is None:
            site = Site(url=website_url, website_id=web.id)    
        site.scanning = True
        db.session.add(site)
        db.session.commit()
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
            log_message(f"Generating report for {website_url}", 'info')
            report = await generate_report(browser, website=website_url)
            await browser.close()

            web = Website.query.filter_by(base_url=base_url).first()
            if web is None:
                web = Website(url=base_url)
                db.session.add(web)

            site = Site.query.filter_by(url=website_url).first()
            if site is None:
                site = Site(url=website_url, website_id=web.id)
            else: 
                # make sure that the site is associated with the correct website
                if site.website_id != web.id:
                    site.website_id = web.id
            report = Report(report, site_id=site.id)
            site.reports.append(report)
            site.last_scanned = db.func.current_timestamp()
            site.scanning = False
            db.session.add(report)
            db.session.add(site)
            db.session.commit()
            
        return report

async def generate_reports(website: str = "https://resources.cs.rutgers.edu") -> List[AccessibilityReport]:
    
    global sites_done, currently_processing
    
    results: List[AccessibilityReport] = []
    sites_done = set()
    currently_processing = set()
    app = create_app()
    base_url = get_netloc(website)

    with app.app_context():
        
        # Check if website exists if not create one, and set scanning to true
        web = Website.query.filter_by(base_url=base_url).first()
        if web is None:
            web = Website(url=website)
            web.active = True
        web.scanning = True
        db.session.add(web)
        db.session.commit()
            
    

    accessibility = check_url(website)
    if not accessibility:
        log_message(f"Website {website} is not accessible, aborting scan", 'error')
        return []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True,args=['--no-sandbox', '--disable-setuid-sandbox'],)
        q = ListQueue()
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
        
    # save reports to database
    with app.app_context():
        # check if website exists
        
        web = Website.query.filter_by(base_url=base_url).first()
        if web is None:
            web = Website(url=website)
            web.active = True
            web.scanning = False
            db.session.add(web)
    
        log_message(f"Storing {len(results)} reports for {website}", 'info')
        if not web.domain_id:
            log_message(f"Warning website doesnt have an associated domain", 'warning')

        sites = []

        for site_reports in results:
            # check if site exists if not create one
            site = db.session.query(Site).filter_by(url=site_reports['url']).first()
            if site is None:
                site = Site(url=site_reports['url'], website_id=web.id)
                sites.append(site)
            else: 
                if site.website_id != web.id:
                    site.website_id = web.id
            report = Report(site_reports, site_id=site.id)

            
            site.reports.append(report)
            site.last_scanned = db.func.current_timestamp()
            db.session.add(report)
            db.session.add(site)

        
        web.last_scanned = db.func.current_timestamp()
        # add sites to website if site didnt exist
        web.sites.extend(sites)
        web.scanning = False
        db.session.add(web)
        db.session.commit()
        db.session.flush()
        
        
        website = db.session.get(Website, web.id)

        ScanFinishedEmail(website).send()

    return results

def run_scan_site(site :str ="https://resources.cs.rutgers.edu"):
    asyncio.run(generate_single_site_report(site))

def run_scan(website:str = "https://resources.cs.rutgers.edu"):
    asyncio.run(generate_reports(website))
    
if __name__ == "__main__":
    # run_scan(website="https://services.cs.rutgers.edu")
    run_scan(website="https://resources.cs.rutgers.edu")
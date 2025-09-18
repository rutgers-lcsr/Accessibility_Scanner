import asyncio
from typing import List
from playwright.async_api import async_playwright
from mail.emails import ScanFinishedEmail
from scanner.browser.report import AccessibilityReport, generate_report
from scanner.log import log_message
from app import create_app
from models import db
from models.website import Site, Site_Website_Assoc, Website 
from models.report import Report
from scanner.utils.queue import ListQueue
from scanner.utils.service import check_url
from utils.urls import get_full_url, get_netloc, get_site_netloc


#TODO 
# Add try catch around database report transactions to prevent site gettings stuck as scanning
sites_done: set[str] = set()
currently_processing: set[str] = set()


async def process_website(name: int, ace_config:str, tags:List[str], browser, queue: ListQueue, results: List[AccessibilityReport], sites_done: set[str], currently_processing: set[str]) -> AccessibilityReport:
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
            res = await generate_report(browser, website=site, tags=tags, ace_config=ace_config)
            
            if 'error' in res and res['error'] is not None:
                log_message(f"[Worker {name}] Error for {site}: {res['error']}", 'error')
            else:
                # add links to queue if not already processing
                for site_link in res.get('links', []):
                    if not site_link in sites_done and not site_link in currently_processing and not queue.exists(site_link):
                        await queue.put(site_link)
                results.append(res)
        except Exception as e:
            log_message(f"[Worker {name}] Exception for {site}: {str(e)}", 'error')
        finally:
            sites_done.add(site)
            currently_processing.remove(site)
            queue.task_done()
            log_message(f"[Worker {name}] Processed {site}, websites left: {queue.qsize()} currently processing: {len(currently_processing)} sites_done: {len(sites_done)}", 'info')


        

async def generate_single_site_report(site_url:str) -> AccessibilityReport:
    app = create_app()
    with app.app_context():
        try:
            print(f"Generating single site report for {site_url}")
            site = db.session.query(Site).filter_by(url=site_url).first()
            if site is None:
                raise ValueError("Site not found")
            
            tags = site.get_tags()
            ace_config:str = site.ace_config()
            if not tags:
                tags = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']
            log_message(f"Using tags: {tags} for site {site.url}", 'info')
            site.scanning = True
            db.session.add(site)
            db.session.commit()

            async with async_playwright() as p:
                try:
                    browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
                    log_message(f"Generating report for {site_url}", 'info')
                    report = await generate_report(browser, website=site_url, tags=tags, ace_config=ace_config)
                    
                    if 'error' in report and report['error'] is not None:
                        log_message(f"Error for {site_url}: {report['error']}", 'error')
                        raise ValueError(report['error'])
                    
                    await browser.close()

                    site = db.session.query(Site).filter_by(url=site_url).first()
                    if site is None:
                        raise ValueError("Site not found after scan")
                    report = Report(report, site_id=site.id)
                    site.reports.append(report)
                     
                    
                    db.session.add(report)
                    db.session.add(site)
                    db.session.commit()
                except Exception as e:
                    log_message(f"Exception generating report for {site_url}: {str(e)}", 'error')
                    raise e
                finally:
                    site = db.session.query(Site).filter_by(url=site_url).first()
                    if not site:
                        raise ValueError("Site not found after scan")
                    site.scanning = False
                    site.last_scanned = db.func.current_timestamp()
                    db.session.add(site)
                    db.session.commit()
            log_message(f"Finished report for {site_url}", 'info')
            return report
        finally:
            site = Site.query.filter_by(url=site_url).first()
            if site:
                site.scanning = False
                db.session.add(site)
                db.session.commit()

async def generate_reports(target_website: str = "https://resources.cs.rutgers.edu") -> List[AccessibilityReport]:
    
    global sites_done, currently_processing
    
    results: List[AccessibilityReport] = []
    sites_done = set()
    currently_processing = set()
    app = create_app()

    with app.app_context():
        
        # Check if website exists if not create one, and set scanning to true
        website = db.session.query(Website).filter_by(url=target_website).first()
        if website is None:
            website = Website(url=target_website)
            website.active = True
        
        
        website.scanning = True
        tags = website.get_tags()
        ace_config = website.get_ace_config()
        if not tags:
            tags = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']
        log_message(f"Using tags: {tags} for website {website.url}", 'info')
        db.session.add(website)
        db.session.commit()


    log_message(f"Starting scan for website: {target_website}", 'info')
    try:
        accessibility = check_url(target_website)
        if not accessibility:
            log_message(f"Website {target_website} is not accessible, aborting scan", 'error')
            return []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True,args=['--no-sandbox', '--disable-setuid-sandbox'],)
            q = ListQueue()
            await q.put(target_website)
            # Launch N workers
            num_workers = 10
            workers = [
                asyncio.create_task(process_website(name = i, browser=browser, queue=q, results=results, sites_done=sites_done, currently_processing=currently_processing, tags=tags, ace_config=ace_config))
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

            website = db.session.query(Website).filter_by(url=target_website).first()
            if website is None:
                website = Website(url=target_website)
                website.active = True
                website.scanning = False
                db.session.add(website)
        
            log_message(f"Storing {len(results)} reports for {target_website}", 'info')
            if not website.domain_id:
                log_message(f"Warning website doesnt have an associated domain", 'warning')


            sitesFound = set()

            for site_reports in results:
                try:
                    
                    # check if site url is based on website domain
                    # this is because some links might be to a redirect domain or external domain, we want to ignore those even though we crawled them
                    site_netloc = get_netloc(site_reports['url'])
                    website_netloc = get_netloc(website.url)
                    if site_netloc != website_netloc:
                        log_message(f"Skipping site {site_reports['url']} as it is not part of the website domain {website_netloc}", 'warning')
                        continue
                    
                    # check if site exists if not create one
                    site = db.session.query(Site).filter_by(url=site_reports['url']).first()
                    
                    if site is None:
                        site = Site(url=site_reports['url'], website=website)
                        db.session.add(site)
                        db.session.flush()
                    else:
                        if site not in website.sites:
                            print(f"Adding site {site.id} to website {website.id}")
                            website.sites.append(site)
                    report = Report(site_reports, site_id=site.id)
                    site.reports.append(report)
                    site.last_scanned = db.func.current_timestamp()
                    sitesFound.add(site.id)
                    site.scanning = False
                    db.session.add(report)
                    db.session.add(site)
                    db.session.commit()
                except Exception as e:
                    log_message(f"Error storing report for {site_reports['url']}: {str(e)}", 'error')
                    db.session.rollback()
                    continue
            websitesToScan = set()
            # remove any sites that were not found in this scan from the website
            for site in website.sites:
                
                if site.id not in sitesFound:
                    log_message(f"Removing site {site.id} from website {website.id} as it was not found in this scan", 'info')
                    
                    associated_websites =site.websites.all() 
                    
                    # If site has mutliple websites remove the association only
                    if len(associated_websites) > 1:
                        site.websites.remove(website)
                        
                        for w in associated_websites:
                            if w.id != website.id:
                                websitesToScan.add(w.url)
                        
                        db.session.add(site)
                        db.session.commit()
                    else:
                        website.sites.remove(site)
                        # Its safe to delete the site
                        
                        Site_Website_Assoc.delete().where(Site_Website_Assoc.c.site_id == site.id).execute()
                        
                        db.session.delete(site)
                        db.session.add(website)
                        db.session.commit()
            
            website.last_scanned = db.func.current_timestamp()
            website.scanning = False
            db.session.add(website)
            db.session.commit()
            
            
            for url in websitesToScan:
                log_message(f"Queueing website {url} for scan as it was linked by a site this is no longer associated with the current site {website.url}", 'info')
                asyncio.get_event_loop().create_task(generate_reports(url))

            
            
            website_doc = db.session.get(Website, website.id)
            ScanFinishedEmail(website_doc).send()
            
            log_message(f"Finished scan for website: {target_website}", 'info')
            return results
    finally:
        with app.app_context():
            website = db.session.query(Website).filter_by(url=target_website).first()
            if website:
                website.scanning = False
                db.session.add(website)
                db.session.commit()

def run_scan_site(site :str ="https://resources.cs.rutgers.edu"):
    asyncio.run(generate_single_site_report(site))

def run_scan(website:str = "https://resources.cs.rutgers.edu"):
    asyncio.run(generate_reports(website))
    
if __name__ == "__main__":
    # run_scan(website="https://services.cs.rutgers.edu")
    run_scan(website="https://resources.cs.rutgers.edu")
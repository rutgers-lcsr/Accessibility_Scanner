import asyncio
from typing import List
import celery
import time
from playwright.async_api import async_playwright
from mail.emails import ScanFinishedEmail
from scanner.browser.report import AccessibilityReport, AccessibilitySummary, generate_report
from scanner.log import log_message
from app import create_app
from models import db
from models.website import Site, Site_Website_Assoc, Website 
from models.report import Report
from scanner.utils.queue import ListQueue
from scanner.utils.service import check_url
from utils.urls import get_full_url, get_netloc, get_site_netloc
from sqlalchemy.exc import OperationalError


# Global sets for tracking scan progress
sites_done: set[str] = set()
currently_processing: set[str] = set()


def commit_with_retry(max_retries=3, retry_delay=1):
    """
    Commit database changes with retry logic for handling database locks.
    Useful for SQLite which can have concurrent access issues.
    """
    for attempt in range(max_retries):
        try:
            db.session.commit()
            return True
        except OperationalError as e:
            if 'database is locked' in str(e) and attempt < max_retries - 1:
                log_message(f"Database locked, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})", 'warning')
                db.session.rollback()
                time.sleep(retry_delay)
            else:
                log_message(f"Database commit failed after {attempt + 1} attempts: {str(e)}", 'error')
                db.session.rollback()
                raise
    return False


async def process_website(name: int, ace_config:str, tags:List[str], browser, queue: ListQueue, results: List[AccessibilitySummary], sites_done: set[str], currently_processing: set[str], website_obj: Website = None, app = None, progress_callback=None, total_sites_ref=None) -> AccessibilityReport:
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
                # Store report immediately to database
                if website_obj and app:
                    await store_report_to_db(res, website_obj, app)
                
                # add links to queue if not already processing
                for site_link in res.get('links', []):
                    if not site_link in sites_done and not site_link in currently_processing and not queue.exists(site_link):
                        await queue.put(site_link)
                        # Update total discovered sites
                        if total_sites_ref is not None:
                            total_sites_ref['count'] = queue.qsize() + len(currently_processing) + len(sites_done)

                summary = AccessibilitySummary(res)
                results.append(summary)

                # Update progress after each successful scan
                if progress_callback and total_sites_ref:
                    current = len(sites_done)
                    total = total_sites_ref['count']
                    progress_callback(current, total)
                    
        except Exception as e:
            log_message(f"[Worker {name}] Exception for {site}: {str(e)}", 'error')
        finally:
            sites_done.add(site)
            currently_processing.remove(site)
            queue.task_done()
            log_message(f"[Worker {name}] Processed {site}, websites left: {queue.qsize()} currently processing: {len(currently_processing)} sites_done: {len(sites_done)}", 'info')


async def store_report_to_db(site_report: AccessibilityReport, website: Website, app):
    """Store a single report to the database immediately after scanning."""
    def _store_in_db():
        with app.app_context():
            try:
                # Check if site url is based on website domain
                site_netloc = get_netloc(site_report['url'])
                website_netloc = get_netloc(website.url)
                if site_netloc != website_netloc:
                    log_message(f"Skipping site {site_report['url']} as it is not part of the website domain {website_netloc}", 'warning')
                    return None
                
                # Re-query website in this session
                website_db = db.session.query(Website).filter_by(id=website.id).first()
                if not website_db:
                    log_message(f"Website {website.id} not found in database", 'error')
                    return None
                
                # Check if site exists if not create one
                site = db.session.query(Site).filter_by(url=site_report['url']).first()
                
                if site is None:
                    site = Site(url=site_report['url'], website=website_db)
                    db.session.add(site)
                    db.session.flush()
                else:
                    if site not in website_db.sites:
                        website_db.sites.append(site)
                
                report = Report(site_report, site_id=site.id)
                site.reports.append(report)
                site.last_scanned = db.func.current_timestamp()
                site.scanning = False
                db.session.add(report)
                db.session.add(site)
                commit_with_retry()
                return site.id
            except Exception as e:
                log_message(f"Error storing report for {site_report['url']}: {str(e)}", 'error')
                db.session.rollback()
                return None
            finally:
                # Always remove the session to prevent 'prepared' state issues
                db.session.remove()
    
    # Run the database operation in a thread to avoid blocking
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _store_in_db)


        

async def generate_single_site_report(site_url:str) -> AccessibilityReport:
    app = create_app()
    scan_error = None
    report_result = None
    
    with app.app_context():
        try:
            log_message(f"Generating single site report for {site_url}", 'info')
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
            commit_with_retry()

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
                log_message(f"Generating report for {site_url}", 'info')
                report = await generate_report(browser, website=site_url, tags=tags, ace_config=ace_config)
                
                if 'error' in report and report['error'] is not None:
                    log_message(f"Error for {site_url}: {report['error']}", 'error')
                    scan_error = ValueError(report['error'])
                else:
                    await browser.close()

                    site = db.session.query(Site).filter_by(url=site_url).first()
                    if site is None:
                        scan_error = ValueError("Site not found after scan")
                    else:
                        report_obj = Report(report, site_id=site.id)
                        site.reports.append(report_obj)
                        site.last_scanned = db.func.current_timestamp()
                        
                        db.session.add(report_obj)
                        db.session.add(site)
                        commit_with_retry()
                        report_result = report
                        
            log_message(f"Finished report for {site_url}", 'info')
            
        except Exception as e:
            log_message(f"Exception generating report for {site_url}: {str(e)}", 'error')
            scan_error = e
        finally:
            # Always clean up scanning state - do not raise exceptions here
            try:
                site = db.session.query(Site).filter_by(url=site_url).first()
                if site:
                    site.scanning = False
                    db.session.add(site)
                    commit_with_retry()
            except Exception as e:
                log_message(f"Error cleaning up scanning state for {site_url}: {str(e)}", 'warning')
                try:
                    db.session.rollback()
                except:
                    pass
            finally:
                try:
                    db.session.remove()
                except:
                    pass
    
    # Raise error after cleanup if scan failed
    if scan_error:
        raise scan_error
    
    return report_result

async def generate_reports(target_website: str = "https://resources.cs.rutgers.edu", progress_callback=None, task_id: str = None) -> List[AccessibilitySummary]:
    
    global sites_done, currently_processing

    results: List[AccessibilitySummary] = []
    sites_done = set()
    currently_processing = set()
    total_sites = 0  # Track total discovered sites
    app = create_app()

    with app.app_context():
        
        # Check if website exists if not create one, and set scanning to true
        website = db.session.query(Website).filter_by(url=target_website).first()
        if website is None:
            website = Website(url=target_website)
            website.active = True
        
        
        website.current_task_id = task_id  # Set the current task ID (creation or scan task)
        tags = website.get_tags()
        ace_config = website.get_ace_config()
        if not tags:
            tags = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']
        log_message(f"Using tags: {tags} for website {website.url}", 'info')
        db.session.add(website)
        commit_with_retry()


    log_message(f"Starting scan for website: {target_website}", 'info')
    
    # Get website ID for passing to workers
    website_id = None
    with app.app_context():
        website_obj = db.session.query(Website).filter_by(url=target_website).first()
        if website_obj:
            website_id = website_obj.id
    
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
            
            # Create a simple website object to pass to workers (just ID and URL)
            class WebsiteProxy:
                def __init__(self, id, url):
                    self.id = id
                    self.url = url
            
            website_proxy = WebsiteProxy(website_id, target_website) if website_id else None
            
            # Create a mutable reference for tracking total sites discovered
            total_sites_ref = {'count': 1}  # Start with 1 (the initial site)
            
            workers = [
                asyncio.create_task(process_website(
                    name=i, 
                    browser=browser, 
                    queue=q, 
                    results=results, 
                    sites_done=sites_done, 
                    currently_processing=currently_processing, 
                    tags=tags, 
                    ace_config=ace_config,
                    website_obj=website_proxy,
                    app=app,
                    progress_callback=progress_callback,
                    total_sites_ref=total_sites_ref
                ))
                for i in range(num_workers)
            ]

            # Wait until all items are processed
            await q.join()

            # Stop workers
            for _ in range(num_workers):
                await q.put(None)
            await asyncio.gather(*workers)
            
        # Cleanup: Remove orphaned sites and finalize scan
        with app.app_context():
            try:
                website = db.session.query(Website).filter_by(url=target_website).first()
                if website is None:
                    log_message(f"Website {target_website} not found after scan", 'error')
                    return results
            
                log_message(f"Scan completed for {target_website}. Processed {len(results)} sites", 'info')
                
                if not website.domain_id:
                    log_message(f"Warning: website {website.url} doesn't have an associated domain", 'warning')

                # Get list of site IDs found in this scan
                sitesFound = set()
                for site_report in results:
                    # Check if the site URL matches the website domain
                    site_netloc = get_netloc(site_report['url'])
                    website_netloc = get_netloc(website.url)
                    if site_netloc == website_netloc:
                        site = db.session.query(Site).filter_by(url=site_report['url']).first()
                        if site:
                            sitesFound.add(site.id)

                websitesToScan = set()
                # Remove any sites that were not found in this scan from the website
                for site in list(website.sites):  # Use list() to avoid modification during iteration
                    if site.id not in sitesFound:
                        log_message(f"Removing site {site.id} from website {website.id} as it was not found in this scan", 'info')
                        
                        associated_websites = site.websites.all() 
                        
                        # If site has multiple websites, remove only the association
                        if len(associated_websites) > 1:
                            site.websites.remove(website)
                            
                            for w in associated_websites:
                                if w.id != website.id:
                                    websitesToScan.add(w.url)
                            
                            db.session.add(site)
                            commit_with_retry()
                        else:
                            # Safe to delete the site entirely
                            website.sites.remove(site)
                            Site_Website_Assoc.delete().where(Site_Website_Assoc.c.site_id == site.id)
                            db.session.delete(site)
                            db.session.add(website)
                            commit_with_retry()
                
                website.last_scanned = db.func.current_timestamp()
                website.current_task_id = None
                db.session.add(website)
                commit_with_retry()
                
                # Queue any websites that need rescanning
                for url in websitesToScan:
                    log_message(f"Queueing website {url} for scan as it was linked by a site no longer associated with {website.url}", 'info')
                    asyncio.get_event_loop().create_task(generate_reports(url))
                
                # Send scan completion email
                website_doc = db.session.get(Website, website.id)
                ScanFinishedEmail(website_doc).send()
                
                log_message(f"Finished scan for website: {target_website}", 'info')
                return results
            except Exception as e:
                log_message(f"Error in cleanup for {target_website}: {str(e)}", 'error')
                db.session.rollback()
                raise
            finally:
                db.session.remove()
    finally:
        with app.app_context():
            try:
                website = db.session.query(Website).filter_by(url=target_website).first()
                if website:
                    website.current_task_id = None
                    db.session.add(website)
                    commit_with_retry()
            except Exception as e:
                log_message(f"Error in finally block for {target_website}: {str(e)}", 'error')
                db.session.rollback()
            finally:
                db.session.remove()

def run_scan_site(site :str ="https://resources.cs.rutgers.edu"):
    asyncio.run(generate_single_site_report(site))

def run_scan(website:str = "https://resources.cs.rutgers.edu"):
    asyncio.run(generate_reports(website))
    
if __name__ == "__main__":
    # run_scan(website="https://services.cs.rutgers.edu")
    run_scan(website="https://resources.cs.rutgers.edu")
    
    
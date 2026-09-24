import asyncio
from typing import List
from urllib import robotparser
import requests
import time
from flask import current_app, has_app_context
from playwright.async_api import async_playwright
from mail.emails import ScanFinishedEmail, ScanRegressionEmail
from scanner.browser.parse import document_type
from scanner.browser.report import ACCESSIBILITY_USER_AGENT, AccessibilityReport, AccessibilitySummary, generate_report
from scanner.log import log_message
from app import create_app
from models import db
from models.website import Site, Site_Website_Assoc, Website 
from models.report import Report
from models.settings import Settings
from scanner.utils.queue import ListQueue
from scanner.utils.service import check_url
from services.findings import changes_for_sites, is_regression, refresh_suppressed_counts, sync_report_findings
from utils.urls import get_full_url, get_netloc, get_site_netloc, get_website_url, normalize_url
from sqlalchemy.exc import IntegrityError, OperationalError


# --disable-dev-shm-usage: Chromium otherwise uses /dev/shm, which is 64 MB in Docker by
# default and makes heavy pages crash the renderer.
BROWSER_ARGS = ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
DEFAULT_PAGE_CONCURRENCY = 3
DEFAULT_MAX_PAGES = 500
DEFAULT_MAX_DEPTH = 5
DEFAULT_CRAWL_DELAY_MS = 250
# The token sites can use in robots.txt to address this scanner specifically.
ROBOTS_AGENT = 'LCSRAccessibility'


def _int_setting(key: str, default: int) -> int:
    try:
        return max(0, int(Settings.get(key=key, default=str(default))))
    except (TypeError, ValueError):
        return default


def page_concurrency() -> int:
    """Pages audited concurrently within one scan (Settings key scan_page_concurrency)."""
    return max(1, _int_setting('scan_page_concurrency', DEFAULT_PAGE_CONCURRENCY))


def crawl_limits() -> dict:
    """Crawl budget from Settings: max pages per scan, max link depth from the start
    page, and the pause before each page request (politeness)."""
    return {
        'max_pages': max(1, _int_setting('max_pages', DEFAULT_MAX_PAGES)),
        'max_depth': _int_setting('max_depth', DEFAULT_MAX_DEPTH),
        'crawl_delay': _int_setting('crawl_delay_ms', DEFAULT_CRAWL_DELAY_MS) / 1000,
    }


def load_robots(website_url: str) -> robotparser.RobotFileParser | None:
    """Parse the website's robots.txt, or return None (everything allowed) when there is
    none or it cannot be read. Redirects are not followed, so this cannot be bounced off
    the (already allow-listed) origin."""
    url = get_website_url(website_url) + '/robots.txt'
    try:
        response = requests.get(url, timeout=10, allow_redirects=False, headers={'User-Agent': ACCESSIBILITY_USER_AGENT})
    except Exception as e:
        log_message(f"Could not fetch {url}: {e}", 'warning')
        return None
    if response.status_code != 200:
        return None
    parser = robotparser.RobotFileParser()
    parser.parse(response.text.splitlines())
    return parser


def get_app():
    """The Flask app to run under: the current one when a Celery task already provides a
    context (celery_app.ContextTask), otherwise a new instance for command-line use."""
    if has_app_context():
        return current_app._get_current_object()
    return create_app()


def crawl_start_urls(website: Website) -> List[str]:
    """Pages a full scan is seeded with: the website URL and its extra start pages
    (Website.set_extra_start_urls), normalised, de-duplicated, root first. Every one is
    crawled at depth 0, so sections that are not linked from the root are still audited."""
    seeds = [normalize_url(website.url)]
    for url in website.get_extra_start_urls():
        url = normalize_url(url)
        if url not in seeds:
            seeds.append(url)
    return seeds


def commit_with_retry(max_retries=3, retry_delay=1):
    """
    Commit database changes with retry logic for transient failures: SQLite lock
    contention locally, deadlocks and lock-wait timeouts on MariaDB.
    """
    for attempt in range(max_retries):
        try:
            db.session.commit()
            return True
        except OperationalError as e:
            if attempt < max_retries - 1:
                log_message(f"Database commit failed, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries}): {e}", 'warning')
                db.session.rollback()
                time.sleep(retry_delay)
            else:
                log_message(f"Database commit failed after {attempt + 1} attempts: {str(e)}", 'error')
                db.session.rollback()
                raise
    return False


async def process_website(name: int, ace_config:str, tags:List[str], browser, queue: ListQueue, results: List[AccessibilitySummary], sites_done: set[str], currently_processing: set[str], website_obj: Website = None, app = None, progress_callback=None, total_sites_ref=None, limits: dict = None, depths: dict = None, robots: robotparser.RobotFileParser = None, documents: dict = None) -> AccessibilityReport:
    """Crawl worker. ``limits`` (see crawl_limits) bounds the crawl, ``depths`` maps each
    queued URL to its link depth from the start page, ``robots`` filters disallowed URLs,
    ``documents`` collects ``{url: {'type', 'pages'}}`` for the document inventory."""
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
            if robots is not None and not robots.can_fetch(ROBOTS_AGENT, site):
                log_message(f"[Worker {name}] Skipping {site}: disallowed by robots.txt", 'info')
                continue
            if limits and limits['crawl_delay']:
                await asyncio.sleep(limits['crawl_delay'])

            res = await generate_report(browser, website=site, tags=tags, ace_config=ace_config)
            
            if 'error' in res and res['error'] is not None:
                log_message(f"[Worker {name}] Error for {site}: {res['error']}", 'error')
                # Record the failure on the page so the UI can show why it has no new
                # report, and count the page as found so cleanup does not drop it.
                if website_obj and app:
                    await store_failure_to_db(res, website_obj, app)
                results.append(AccessibilitySummary.from_report(res))
            else:
                # Store report immediately to database
                if website_obj and app:
                    await store_report_to_db(res, website_obj, app)
                
                # Documents are inventoried, never queued as pages.
                if documents is not None:
                    for doc_url in res.get('documents') or []:
                        doc_type = document_type(doc_url)
                        if doc_type:
                            documents.setdefault(doc_url, {'type': doc_type, 'pages': set()})['pages'].add(site)

                # add links to queue if not already processing
                depth = depths.get(site, 0) if depths is not None else 0
                for site_link in res.get('links', []):
                    site_link = normalize_url(site_link)
                    if site_link in sites_done or site_link in currently_processing or queue.exists(site_link):
                        continue
                    if limits:
                        if depth + 1 > limits['max_depth']:
                            continue
                        if queue.qsize() + len(currently_processing) + len(sites_done) >= limits['max_pages']:
                            log_message(f"[Worker {name}] Page budget of {limits['max_pages']} reached; not queueing more links", 'warning')
                            break
                    if depths is not None:
                        depths[site_link] = depth + 1
                    await queue.put(site_link)
                    # Update total discovered sites
                    if total_sites_ref is not None:
                        total_sites_ref['count'] = queue.qsize() + len(currently_processing) + len(sites_done)

                results.append(AccessibilitySummary.from_report(res))

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


def _attach_findings(report: Report, site: Site) -> None:
    """Bring the page's findings in line with a report that has just been committed.

    Runs in its own transaction: a failure here (for instance two scans of the same
    page racing on the unique fingerprint) is logged, leaves the report in place with
    ``suppressed_counts`` NULL, and ``flask findings backfill`` repairs it later.
    """
    try:
        sync_report_findings(site.id, report.id, report.timestamp, (report.report or {}).get('violations') or [])
        refresh_suppressed_counts(site.id, report.id)
        commit_with_retry()
    except Exception as e:
        log_message(f"Finding sync failed for {report.url}: {e}", 'error')
        db.session.rollback()


async def store_report_to_db(site_report: AccessibilityReport, website: Website, app):
    """Store a single report to the database immediately after scanning."""
    def _store_in_db():
        with app.app_context():
            try:
                # Check if site url is based on website domain
                site_netloc = get_netloc(site_report['url']).lower()
                website_netloc = get_netloc(website.url).lower()
                if site_netloc != website_netloc:
                    log_message(f"Skipping site {site_report['url']} as it is not part of the website domain {website_netloc}", 'warning')
                    return None

                # Re-query website in this session
                website_db = db.session.query(Website).filter_by(id=website.id).first()
                if not website_db:
                    log_message(f"Website {website.id} not found in database", 'error')
                    return None

                site = _get_or_create_site(site_report['url'], website_db.id)
                
                report = Report(site_report, site_id=site.id)
                site.reports.append(report)
                site.last_scanned = db.func.current_timestamp()
                site.scanning = False
                site.last_scan_status = 'completed'
                site.last_scan_error = None
                db.session.add(report)
                db.session.add(site)
                commit_with_retry()
                _attach_findings(report, site)
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


def _get_or_create_site(url: str, website_id: int) -> Site:
    """Return the Site for ``url`` attached to website ``website_id``, creating it if needed.

    Concurrent workers can race on the same URL. site.url is unique, so the loser's
    insert fails (IntegrityError, or ValueError when Site.__init__ already sees the
    winner's row); it then rolls back and re-reads in a new transaction. The rollback
    matters: under repeatable-read isolation the same transaction would never see the
    row the other worker committed.
    """
    website_db = db.session.get(Website, website_id)
    site = db.session.query(Site).filter_by(url=url).first()
    if site is None:
        try:
            site = Site(url=url, website=website_db)
            db.session.add(site)
            db.session.flush()
            return site
        except (IntegrityError, ValueError):
            db.session.rollback()
            website_db = db.session.get(Website, website_id)
            site = db.session.query(Site).filter_by(url=url).first()
            if site is None:
                raise
    if site not in website_db.sites:
        website_db.sites.append(site)
    return site


async def store_failure_to_db(site_report: AccessibilityReport, website: Website, app):
    """Record a failed page scan on its Site row (created if needed).

    Nothing is written to the report table, so "latest report" queries keep showing the
    last successful audit; the failure is visible through last_scan_status/error.
    """
    def _store_in_db():
        with app.app_context():
            try:
                if get_netloc(site_report['url']).lower() != get_netloc(website.url).lower():
                    return None

                website_db = db.session.query(Website).filter_by(id=website.id).first()
                if not website_db:
                    return None

                site = _get_or_create_site(site_report['url'], website_db.id)
                site.scanning = False
                site.last_scan_status = 'failed'
                site.last_scan_error = (site_report.get('error') or 'Unknown error')[:2000]
                db.session.add(site)
                commit_with_retry()
                return site.id
            except Exception as e:
                log_message(f"Error recording failure for {site_report['url']}: {e}", 'error')
                db.session.rollback()
                return None
            finally:
                db.session.remove()

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _store_in_db)


        

async def run_quick_scan(url: str, tags: List[str], ace_config: str) -> AccessibilityReport:
    """Audit one page without touching the database (quick scans)."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=BROWSER_ARGS)
        try:
            return await generate_report(browser, website=url, tags=tags, ace_config=ace_config)
        finally:
            await browser.close()


async def generate_single_site_report(site_url:str) -> int | None:
    """Scan one page and store its report; returns the report id (None if nothing was stored)."""
    app = get_app()
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
                browser = await p.chromium.launch(headless=True, args=BROWSER_ARGS)
                try:
                    log_message(f"Generating report for {site_url}", 'info')
                    report = await generate_report(browser, website=site_url, tags=tags, ace_config=ace_config)
                finally:
                    await browser.close()

                if 'error' in report and report['error'] is not None:
                    log_message(f"Error for {site_url}: {report['error']}", 'error')
                    scan_error = ValueError(report['error'])
                else:
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
                        _attach_findings(report_obj, site)
                        report_result = report_obj.id
                        
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
                    site.last_scan_status = 'failed' if scan_error else 'completed'
                    site.last_scan_error = str(scan_error)[:2000] if scan_error else None
                    db.session.add(site)
                    commit_with_retry()
            except Exception as e:
                log_message(f"Error cleaning up scanning state for {site_url}: {str(e)}", 'warning')
                try:
                    db.session.rollback()
                except Exception:
                    pass
            finally:
                try:
                    db.session.remove()
                except Exception:
                    pass
    
    # Raise error after cleanup if scan failed
    if scan_error:
        raise scan_error
    
    return report_result

async def generate_reports(target_website: str = "https://resources.cs.rutgers.edu", progress_callback=None, task_id: str = None) -> List[AccessibilitySummary]:
    results: List[AccessibilitySummary] = []
    sites_done: set[str] = set()
    currently_processing: set[str] = set()
    documents: dict = {}
    app = get_app()

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
        num_workers = page_concurrency()
        limits = crawl_limits()
        start_urls = crawl_start_urls(website)


    log_message(f"Starting scan for website: {target_website}", 'info')
    # Written to the website when the scan ends, whatever the outcome.
    outcome = {'status': 'failed', 'error': 'Scan did not complete'}
    
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
            outcome.update(status='unreachable', error='The website did not respond to the reachability check')
            return []

        robots = await asyncio.get_event_loop().run_in_executor(None, load_robots, target_website)
        log_message(f"Crawl limits for {target_website}: {limits}, robots.txt {'loaded' if robots else 'not used'}", 'info')
        if len(start_urls) > 1:
            log_message(f"Extra start pages for {target_website}: {start_urls[1:]}", 'info')

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=BROWSER_ARGS)
            q = ListQueue()
            depths = {}
            for start_url in start_urls:
                await q.put(start_url)
                depths[start_url] = 0
            workers = []

            # Create a simple website object to pass to workers (just ID and URL)
            class WebsiteProxy:
                def __init__(self, id, url):
                    self.id = id
                    self.url = url
            
            website_proxy = WebsiteProxy(website_id, target_website) if website_id else None
            
            # Create a mutable reference for tracking total sites discovered
            total_sites_ref = {'count': len(start_urls)}
            
            try:
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
                        total_sites_ref=total_sites_ref,
                        limits=limits,
                        depths=depths,
                        robots=robots,
                        documents=documents,
                    ))
                    for i in range(num_workers)
                ]

                # Wait until all items are processed
                await q.join()

                # Stop workers
                for _ in range(num_workers):
                    await q.put(None)
                await asyncio.gather(*workers)
            except BaseException:
                # Cancelled (soft time limit) or a worker failed: stop the others so the
                # browser can be closed instead of leaving Chromium processes behind.
                for worker in workers:
                    worker.cancel()
                await asyncio.gather(*workers, return_exceptions=True)
                raise
            finally:
                await browser.close()
            
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
                    site_netloc = get_netloc(site_report.url).lower()
                    website_netloc = get_netloc(website.url).lower()
                    if site_netloc == website_netloc:
                        site = db.session.query(Site).filter_by(url=site_report.url).first()
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

                # Document inventory: what the crawl linked to, then the basic PDF checks.
                # Neither may fail the scan.
                try:
                    from services.documents import check_website_documents, sync_documents  # local import
                    sync_documents(website.id, documents)
                    check_website_documents(website.id, robots=robots, crawl_delay=limits['crawl_delay'])
                except Exception as e:
                    log_message(f"Document inventory failed for {target_website}: {e}", 'error')
                    db.session.rollback()
                
                # Queue any websites that need rescanning as their own tasks. (These used
                # to be scheduled on this event loop, which the task closes right after.)
                from services.scan import queue_website_scan  # local import: avoids a circular import
                for url in websitesToScan:
                    other = db.session.query(Website).filter_by(url=url).first()
                    if other is None:
                        continue
                    log_message(f"Queueing website {url} for scan as it was linked by a site no longer associated with {website.url}", 'info')
                    queue_website_scan(other)
                
                # Tell the website's people: a regression gets its own email, otherwise the
                # usual summary. Mail trouble must not turn a finished scan into a failed one.
                website_doc = db.session.get(Website, website.id)
                try:
                    changes = changes_for_sites([row.id for row in website_doc.sites.with_entities(Site.id).all()])
                    if is_regression(changes):
                        ScanRegressionEmail(website_doc, changes).send()
                    else:
                        ScanFinishedEmail(website_doc, changes=changes).send()
                except Exception as e:
                    log_message(f"Error sending scan mail for {target_website}: {e}", 'error')
                    db.session.rollback()
                
                outcome.update(status='completed', error=None)
                log_message(f"Finished scan for website: {target_website}", 'info')
                return results
            except Exception as e:
                log_message(f"Error in cleanup for {target_website}: {str(e)}", 'error')
                db.session.rollback()
                raise
            finally:
                db.session.remove()
    except Exception as e:
        outcome.update(status='failed', error=f"{type(e).__name__}: {e}"[:2000])
        raise
    finally:
        with app.app_context():
            try:
                website = db.session.query(Website).filter_by(url=target_website).first()
                if website:
                    website.current_task_id = None
                    website.last_scan_status = outcome['status']
                    website.last_scan_error = outcome['error']
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
    
    
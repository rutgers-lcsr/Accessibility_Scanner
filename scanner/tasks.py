"""
Celery tasks for website and site scanning.
These tasks are executed by Celery workers in the background.
"""
import asyncio
from typing import List
from datetime import datetime, timedelta
from celery_app import celery
from scanner.log import log_message
from models import db
from models.website import Site, Website
from models.report import Report
from scanner.scan import generate_reports as async_generate_reports, generate_single_site_report as async_generate_single_site_report
from mail.emails import ScanFinishedEmail


@celery.task(name='scanner.tasks.check_and_queue_scans')
def check_and_queue_scans():
    """
    Periodic task that checks all active websites and queues scans for those
    that are due based on their rate_limit (rescan interval).
    
    This replaces the old scanner container's queue_process functionality.
    """
    from app import create_app
    app = create_app()
    
    with app.app_context():
        # Get all active websites
        websites = db.session.query(Website).filter(Website.active == True).all()
        log_message(f"Checking {len(websites)} active websites for scheduled scans", 'info')
        
        queued_count = 0
        for website in websites:
            now = datetime.now()
            
            # Check if website is due for a scan
            # Scan if: never scanned OR last scan was more than rate_limit days ago
            should_scan = (
                website.last_scanned is None or 
                now - website.last_scanned > timedelta(days=website.rate_limit)
            )

            if website.current_task_id:
                websiteTask = scan_website.AsyncResult(website.current_task_id)
                if websiteTask.state in ['PENDING', 'PROGRESS']:
                    continue
                
            if should_scan:
                # Queue the scan task
                log_message(
                    f"Queueing scheduled scan for {website.url} "
                    f"(last scanned: {website.last_scanned or 'never'}, "
                    f"rate limit: {website.rate_limit} days)",
                    'info'
                )
                scan_website.delay(website.url)
                queued_count += 1
        
        log_message(f"Scheduled scan check complete. Queued {queued_count} website scans.", 'info')
        return {
            'checked': len(websites),
            'queued': queued_count
        }


@celery.task(bind=True, name='scanner.tasks.scan_website')
def scan_website(self, website_url: str):
    """
    Celery task to scan an entire website and all its pages.
    Reports are saved to the database incrementally as each page is scanned.
    
    Args:
        website_url: The base URL of the website to scan
        
    Returns:
        dict: Result summary including number of reports generated
    """
    try:
        log_message(f"[Celery Task {self.request.id}] Starting website scan for {website_url}", 'info')
        
        # Update task state
        self.update_state(state='PROGRESS', meta={'status': 'Initializing scan...', 'current': 0, 'total': 0})
        
        # Create a progress callback function
        def update_progress(current: int, total: int, status: str = None):
            meta = {
                'current': current,
                'total': total,
            }
            if status:
                meta['status'] = status
            else:
                meta['status'] = f'Scanning page {current} of {total}'
            
            self.update_state(state='PROGRESS', meta=meta)
            log_message(f"[Celery Task {self.request.id}] Progress: {current}/{total}", 'debug')
        
        # Run the async scanning function
        # Reports are committed to DB incrementally as they're generated
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            results = loop.run_until_complete(
                async_generate_reports(
                    website_url, 
                    progress_callback=update_progress,
                    task_id=self.request.id  # Pass the task ID
                )
            )
            
            self.update_state(state='SUCCESS', meta={
                'status': 'Scan completed',
                'current': len(results),
                'total': len(results)
            })
            
            log_message(
                f"[Celery Task {self.request.id}] Completed website scan for {website_url}. "
                f"Generated {len(results)} reports",
                'info'
            )
            
            return {
                'status': 'completed',
                'website_url': website_url,
                'reports_generated': len(results),
                'sites_scanned': len(results)
            }
        finally:
            loop.close()
            
    except Exception as e:
        log_message(f"[Celery Task {self.request.id}] Error scanning website {website_url}: {str(e)}", 'error')
        self.update_state(state='FAILURE', meta={'status': f'Scan failed: {str(e)}'})
        raise


@celery.task(bind=True, name='scanner.tasks.scan_site')
def scan_site(self, site_url: str):
    """
    Celery task to scan a single site/page.
    
    Args:
        site_url: The URL of the site/page to scan
        
    Returns:
        dict: Result summary including report data
    """
    try:
        log_message(f"[Celery Task {self.request.id}] Starting site scan for {site_url}", 'info')
        
        # Update task state
        self.update_state(state='PROGRESS', meta={'status': 'Scanning site...', 'url': site_url})
        
        # Run the async scanning function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(async_generate_single_site_report(site_url))
            log_message(f"[Celery Task {self.request.id}] Completed site scan for {site_url}", 'info')
            
            return {
                'status': 'completed',
                'site_url': site_url,
                'report_generated': True
            }
        finally:
            loop.close()
            
    except Exception as e:
        log_message(f"[Celery Task {self.request.id}] Error scanning site {site_url}: {str(e)}", 'error')
        self.update_state(state='FAILURE', meta={'status': str(e)})
        raise


@celery.task(bind=True, name='scanner.tasks.rescan_website')
def rescan_website(self, website_id: int):
    """
    Celery task to rescan an existing website by its ID.
    
    Args:
        website_id: The database ID of the website to rescan
        
    Returns:
        dict: Result summary
    """
    from app import create_app
    app = create_app()
    
    try:
        with app.app_context():
            website = db.session.get(Website, website_id)
            if not website:
                raise ValueError(f"Website with ID {website_id} not found")
            
            website_url = website.url
            log_message(f"[Celery Task {self.request.id}] Rescanning website {website_url} (ID: {website_id})", 'info')
        
        # Call the scan_website task (outside app context to avoid conflicts)
        return scan_website(self, website_url)
        
    except Exception as e:
        log_message(f"[Celery Task {self.request.id}] Error rescanning website ID {website_id}: {str(e)}", 'error')
        self.update_state(state='FAILURE', meta={'status': str(e)})
        raise
    finally:
        with app.app_context():
            try:
                db.session.remove()
            except:
                pass


@celery.task(bind=True, name='scanner.tasks.rescan_site')
def rescan_site(self, site_id: int):
    """
    Celery task to rescan an existing site by its ID.
    
    Args:
        site_id: The database ID of the site to rescan
        
    Returns:
        dict: Result summary
    """
    from app import create_app
    app = create_app()
    
    try:
        with app.app_context():
            site = db.session.get(Site, site_id)
            if not site:
                raise ValueError(f"Site with ID {site_id} not found")
            
            site_url = site.url
            log_message(f"[Celery Task {self.request.id}] Rescanning site {site_url} (ID: {site_id})", 'info')
        
        # Call the scan_site task (outside app context to avoid conflicts)
        return scan_site(self, site_url)
        
    except Exception as e:
        log_message(f"[Celery Task {self.request.id}] Error rescanning site ID {site_id}: {str(e)}", 'error')
        self.update_state(state='FAILURE', meta={'status': str(e)})
        raise
    finally:
        with app.app_context():
            try:
                db.session.remove()
            except:
                pass

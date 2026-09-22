"""
Celery tasks for website and site scanning.
These tasks are executed by Celery workers in the background.
"""
import asyncio
from typing import List
from datetime import datetime, timedelta
from celery.exceptions import SoftTimeLimitExceeded
from celery_app import celery
from scanner.log import log_message
from models import db
from models.website import Site, Website
from models.report import Report
from scanner.scan import generate_reports as async_generate_reports, generate_single_site_report as async_generate_single_site_report
from mail.emails import ScanFinishedEmail


def _run_scan(loop: asyncio.AbstractEventLoop, coro, label: str):
    """Run a scan coroutine to completion on ``loop``.

    When Celery's soft time limit fires, the exception can surface either inside the
    coroutine (which then unwinds normally) or out of the event loop with the scan
    still pending. In the latter case the scan is cancelled and the loop is run again
    so its finally blocks close the browser before the task fails.
    """
    scan = loop.create_task(coro)
    try:
        return loop.run_until_complete(scan)
    except SoftTimeLimitExceeded:
        log_message(f"Soft time limit reached during {label}; cancelling and cleaning up", 'error')
        if not scan.done():
            scan.cancel()
            loop.run_until_complete(asyncio.gather(scan, return_exceptions=True))
        raise


@celery.task(name='scanner.tasks.check_and_queue_scans')
def check_and_queue_scans():
    """
    Periodic task that checks all active websites and queues scans for those
    that are due based on their rate_limit (rescan interval).

    Runs inside the app context provided by celery_app.ContextTask. Queueing goes
    through services.scan so the website records the task id exactly as a manual
    scan does; otherwise a backed-up queue received the same website every tick.
    """
    from services.scan import queue_website_scan  # local import: avoids a circular import

    websites = db.session.query(Website).filter(Website.active == True).all()
    log_message(f"Checking {len(websites)} active websites for scheduled scans", 'info')

    queued_count = 0
    for website in websites:
        now = datetime.now()

        # Scan if: never scanned OR last scan was more than rate_limit days ago
        should_scan = (
            website.last_scanned is None or
            now - website.last_scanned > timedelta(days=website.rate_limit)
        )
        if not should_scan:
            continue

        _, queued = queue_website_scan(website)
        if queued:
            log_message(
                f"Queueing scheduled scan for {website.url} "
                f"(last scanned: {website.last_scanned or 'never'}, "
                f"rate limit: {website.rate_limit} days)",
                'info'
            )
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
            results = _run_scan(loop, async_generate_reports(
                website_url,
                progress_callback=update_progress,
                task_id=self.request.id  # Pass the task ID
            ), f"website scan for {website_url}")

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
        # Celery records the exception as the FAILURE result; nothing to set by hand.
        log_message(f"[Celery Task {self.request.id}] Error scanning website {website_url}: {str(e)}", 'error')
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
            _run_scan(loop, async_generate_single_site_report(site_url), f"site scan for {site_url}")
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
        raise


@celery.task(bind=True, name='scanner.tasks.rescan_website')
def rescan_website(self, website_id: int):
    """Queue a fresh scan of an existing website by its ID.

    Queues a separate scan_website task (it used to call the bound task as a plain
    function, running it in-process under this task's id).
    """
    from services.scan import queue_website_scan  # local import: avoids a circular import

    website = db.session.get(Website, website_id)
    if not website:
        raise ValueError(f"Website with ID {website_id} not found")

    log_message(f"[Celery Task {self.request.id}] Rescanning website {website.url} (ID: {website_id})", 'info')
    task_id, queued = queue_website_scan(website)
    return {
        'status': 'queued' if queued else 'already running',
        'website_url': website.url,
        'task_id': task_id,
    }


@celery.task(bind=True, name='scanner.tasks.rescan_site')
def rescan_site(self, site_id: int):
    """Queue a fresh scan of an existing site by its ID (see rescan_website)."""
    from services.scan import queue_site_scan, site_scan_in_progress  # local import

    site = db.session.get(Site, site_id)
    if not site:
        raise ValueError(f"Site with ID {site_id} not found")

    log_message(f"[Celery Task {self.request.id}] Rescanning site {site.url} (ID: {site_id})", 'info')
    if site_scan_in_progress(site):
        return {'status': 'already running', 'site_url': site.url, 'task_id': site.last_task_id}
    task_id = queue_site_scan(site)
    return {'status': 'queued', 'site_url': site.url, 'task_id': task_id}


@celery.task(name='scanner.tasks.send_admin_digest')
def send_admin_digest():
    """Weekly system digest to site admins (scheduled by beat), unless switched off in
    Settings (admin_digest_enabled)."""
    from mail.emails import AdminDigestEmail
    from models.settings import Settings

    if (Settings.get('admin_digest_enabled') or '').lower() != 'true':
        log_message("Admin digest is switched off in Settings", 'info')
        return {'sent': False, 'recipients': 0}
    sender = AdminDigestEmail()
    sent = sender.send()
    return {'sent': sent, 'recipients': len(sender.msg.recipients) if sent and sender.msg else 0}

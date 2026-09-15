"""Scan queueing and task-status helpers shared by the JWT and API-key blueprints.

Both blueprints used to carry their own copy of "check in progress -> queue -> record
task id -> serialise AsyncResult". Keeping it here means the two surfaces cannot drift
(the JWT site-scan path, for instance, never recorded a task id at all).
"""
import celery.result

from models import db
from models.website import Site, Website
from scanner.tasks import scan_site as scan_site_task
from scanner.tasks import scan_website as scan_website_task

# Celery reports an unknown or expired task id as PENDING too; treating it as
# "running" is what strands a website after a worker crash. Tightened in a
# follow-up that records scan_started_at.
IN_PROGRESS_STATES = ('PENDING', 'PROGRESS')


def scan_in_progress(task_id: str | None) -> bool:
    if not task_id:
        return False
    return scan_website_task.AsyncResult(task_id).state in IN_PROGRESS_STATES


def queue_website_scan(website: Website) -> tuple[str, bool]:
    """Queue a crawl of ``website`` unless one is already running.

    Returns ``(task_id, queued)``; ``queued`` is False when the existing task id was
    returned instead.
    """
    if scan_in_progress(website.current_task_id):
        return website.current_task_id, False

    task = scan_website_task.delay(website.url)
    website.current_task_id = task.id
    # last_task_id is never cleared, so status polling can still resolve the owner
    # after the scan finishes and current_task_id is reset.
    website.last_task_id = task.id
    db.session.commit()
    return task.id, True


def queue_site_scan(site: Site) -> str:
    """Queue a scan of a single page. Callers check ``site.scanning`` first."""
    task = scan_site_task.delay(site.url)
    site.last_task_id = task.id
    db.session.commit()
    return task.id


def resolve_task_target(task_id: str) -> Website | Site | None:
    """Return the Website or Site whose most recent scan is ``task_id``."""
    website = db.session.query(Website).filter_by(last_task_id=task_id).first()
    if website:
        return website
    return db.session.query(Site).filter_by(last_task_id=task_id).first()


def serialize_task_state(task_id: str) -> dict:
    """Describe a Celery task for status polling.

    Always includes ``task_id`` and ``state``; PROGRESS adds ``status``/``current``/
    ``total``, SUCCESS adds ``result`` and FAILURE puts the error text in ``status``.
    """
    from celery_app import celery as celery_app

    task = celery.result.AsyncResult(task_id, app=celery_app)
    state = task.state
    response = {'task_id': task_id, 'state': state}

    if state == 'PENDING':
        response['status'] = 'Task is waiting to be executed...'
    elif state == 'PROGRESS':
        info = task.info or {}
        response['status'] = info.get('status', '')
        response['current'] = info.get('current', 0)
        response['total'] = info.get('total', 1)
    elif state == 'SUCCESS':
        response['result'] = task.result
    else:  # FAILURE, REVOKED, RETRY, ...
        response['status'] = str(task.info) if task.info else ''

    return response

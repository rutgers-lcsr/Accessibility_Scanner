"""Quick scans: audit one page ad hoc, keep the result briefly, store nothing else.

The task returns a bounded, JSON-safe result (shape_result): violations and incomplete
rules with at most QUICK_SCAN_MAX_NODES elements each, the counts, and the screenshot
as base64 when it fits in QUICK_SCAN_MAX_PHOTO_BYTES (downscaled once if not).
"""
import base64
import io
from datetime import datetime, timedelta, timezone

import celery.result

from models import db
from models.quick_scan import QuickScan
from models.report import compute_report_counts
from models.user import User
from scanner.tasks import quick_scan as quick_scan_task

QUICK_SCAN_RESULT_TTL = timedelta(hours=24)
QUICK_SCAN_MAX_PHOTO_BYTES = 2_000_000
QUICK_SCAN_MAX_NODES = 50
ACTIVE_STATES = ('STARTED', 'PROGRESS', 'RETRY')
# A quick scan has its own time limit (scanner.tasks.quick_scan); anything still
# PENDING after this is treated as lost rather than blocking the user.
IN_PROGRESS_WINDOW = timedelta(minutes=10)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _cap_nodes(rules) -> list:
    capped = []
    for rule in rules or []:
        nodes = rule.get('nodes') or []
        entry = dict(rule)
        entry['nodes'] = nodes[:QUICK_SCAN_MAX_NODES]
        entry['nodes_truncated'] = max(0, len(nodes) - QUICK_SCAN_MAX_NODES)
        capped.append(entry)
    return capped


def _encode_photo(photo) -> tuple:
    """``(base64 or None, omitted)``: a screenshot over the size cap is downscaled once
    with Pillow; if it still does not fit it is left out."""
    if not photo:
        return None, False
    if len(photo) > QUICK_SCAN_MAX_PHOTO_BYTES:
        try:
            from PIL import Image

            image = Image.open(io.BytesIO(photo))
            image.thumbnail((1400, 8000))
            buffer = io.BytesIO()
            image.save(buffer, format='PNG', optimize=True)
            photo = buffer.getvalue()
        except Exception:
            return None, True
        if len(photo) > QUICK_SCAN_MAX_PHOTO_BYTES:
            return None, True
    return base64.b64encode(photo).decode('ascii'), False


def shape_result(report: dict) -> dict:
    """The Celery result of a quick scan, from generate_report's dict."""
    result = {
        'status': 'failed' if report.get('error') else 'completed',
        'url': report.get('url'),
        'timestamp': report.get('timestamp'),
        'error': report.get('error'),
        'response_code': report.get('response_code'),
        'tags': report.get('tags') or [],
        'report_counts': None,
        'report': None,
        'photo': None,
        'photo_omitted': False,
        'links': len(report.get('links') or []),
        'videos': len(report.get('videos') or []),
        'tabable': report.get('tabable'),
    }
    if result['status'] == 'failed':
        return result
    axe = report.get('report') or {}
    result['report_counts'] = compute_report_counts(axe)
    result['report'] = {
        'violations': _cap_nodes(axe.get('violations')),
        'incomplete': _cap_nodes(axe.get('incomplete')),
    }
    result['photo'], result['photo_omitted'] = _encode_photo(report.get('photo'))
    return result


def quick_scan_in_progress(user: User) -> bool:
    """One quick scan per user at a time."""
    latest = (
        db.session.query(QuickScan)
        .filter(QuickScan.user_id == user.id, QuickScan.created_at >= _utcnow() - IN_PROGRESS_WINDOW)
        .order_by(QuickScan.created_at.desc(), QuickScan.id.desc())
        .first()
    )
    if latest is None:
        return False
    state = quick_scan_task.AsyncResult(latest.task_id).state
    return state in ACTIVE_STATES or state == 'PENDING'


def queue_quick_scan(user: User, url: str) -> QuickScan:
    QuickScan.prune(_utcnow() - QUICK_SCAN_RESULT_TTL)
    task = quick_scan_task.delay(url)
    quick = QuickScan(task_id=task.id, url=url, user_id=user.id, created_at=_utcnow())
    db.session.add(quick)
    db.session.commit()
    return quick


def quick_scan_state(quick: QuickScan) -> dict:
    """``{state, status|result|error}`` for the result endpoint; PENDING past the TTL
    means the result is gone."""
    from celery_app import celery as celery_app

    task = celery.result.AsyncResult(quick.task_id, app=celery_app)
    state = task.state
    if state == 'SUCCESS':
        return {'state': state, 'result': task.result}
    if state == 'PENDING' and quick.created_at < _utcnow() - QUICK_SCAN_RESULT_TTL:
        return {'state': 'EXPIRED'}
    if state in ('PENDING',) + ACTIVE_STATES:
        info = task.info if isinstance(task.info, dict) else {}
        return {'state': state, 'status': info.get('status') or ('Waiting for a worker…' if state == 'PENDING' else '')}
    return {'state': state, 'error': str(task.info) if task.info else 'The scan failed'}

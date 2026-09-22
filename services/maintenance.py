"""Report retention.

Policy (Settings): keep every report younger than ``retention_keep_days``; between
that and ``retention_max_days`` keep the newest report per calendar month per page and
drop that band's screenshots; delete anything older than ``retention_max_days``. A
page's latest report is never deleted and keeps its screenshot. Nothing runs unless
``retention_enabled`` is true; ``flask maintenance retention --dry-run`` shows the plan.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import update

from models import db
from models.report import Report
from models.settings import Settings
from models.website import Site
from scanner.accessibility.ace import slim_axe_report


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _int_setting(key: str, minimum: int) -> int:
    try:
        return max(minimum, int(Settings.get(key)))
    except (TypeError, ValueError):
        return minimum


def retention_settings() -> dict:
    return {
        'enabled': (Settings.get('retention_enabled') or '').lower() == 'true',
        'keep_days': _int_setting('retention_keep_days', 1),
        'max_days': _int_setting('retention_max_days', 1),
    }


@dataclass
class RetentionPlan:
    delete_ids: list = field(default_factory=list)
    strip_photo_ids: list = field(default_factory=list)
    per_site: list = field(default_factory=list)  # {site_id, url, reports, delete, strip_photos, newest_kept}

    @property
    def summary(self) -> dict:
        return {'sites': len(self.per_site), 'delete': len(self.delete_ids), 'strip_photos': len(self.strip_photo_ids)}


def plan_retention(now: datetime | None = None, keep_days: int | None = None, max_days: int | None = None) -> RetentionPlan:
    """Decide, per page, which reports to delete and which kept reports lose their
    screenshot. One light query; the report JSON and photos are never loaded."""
    settings = retention_settings()
    keep_days = keep_days if keep_days is not None else settings['keep_days']
    max_days = max(max_days if max_days is not None else settings['max_days'], keep_days)
    now = now or _utcnow()
    keep_after = now - timedelta(days=keep_days)
    delete_before = now - timedelta(days=max_days)

    rows = (
        db.session.query(Report.id, Report.site_id, Report.timestamp, Report.photo.isnot(None).label('has_photo'))
        .order_by(Report.site_id, Report.timestamp.desc(), Report.id.desc())
        .all()
    )
    plan = RetentionPlan()
    by_site = {}
    for row in rows:
        by_site.setdefault(row.site_id, []).append(row)
    urls = dict(db.session.query(Site.id, Site.url).filter(Site.id.in_(list(by_site))).all()) if by_site else {}

    for site_id, reports in by_site.items():  # newest first
        delete, strip = [], []
        months_kept = set()
        for index, row in enumerate(reports):
            if index == 0 or row.timestamp >= keep_after:
                continue  # the latest report, or recent: kept as is
            if row.timestamp < delete_before:
                delete.append(row.id)
                continue
            month = (row.timestamp.year, row.timestamp.month)
            if month in months_kept:
                delete.append(row.id)
            else:
                months_kept.add(month)
                if row.has_photo:
                    strip.append(row.id)
        plan.delete_ids.extend(delete)
        plan.strip_photo_ids.extend(strip)
        if delete or strip:
            plan.per_site.append({
                'site_id': site_id, 'url': urls.get(site_id), 'reports': len(reports),
                'delete': len(delete), 'strip_photos': len(strip), 'newest_kept': reports[0].timestamp,
            })
    return plan


def apply_retention(plan: RetentionPlan, batch_size: int = 200, dry_run: bool = False) -> dict:
    """Carry out a plan in batches so MariaDB never holds a long lock. No report row is
    loaded: plain DELETE and UPDATE statements."""
    from scanner.scan import commit_with_retry  # local import: scanner imports services

    result = {'deleted': 0, 'photos_stripped': 0, 'dry_run': dry_run}
    if dry_run:
        result['deleted'] = len(plan.delete_ids)
        result['photos_stripped'] = len(plan.strip_photo_ids)
        return result
    for start in range(0, len(plan.delete_ids), batch_size):
        chunk = plan.delete_ids[start:start + batch_size]
        db.session.execute(Report.__table__.delete().where(Report.id.in_(chunk)))
        commit_with_retry()
        result['deleted'] += len(chunk)
    for start in range(0, len(plan.strip_photo_ids), batch_size):
        chunk = plan.strip_photo_ids[start:start + batch_size]
        db.session.execute(update(Report.__table__).where(Report.id.in_(chunk)).values(photo=None))
        commit_with_retry()
        result['photos_stripped'] += len(chunk)
    return result


def slim_stored_reports(batch_size: int = 200, dry_run: bool = False, log=None) -> dict:
    """Backfill slim_axe_report over reports stored before slimming, and drop the
    phantom 'inaccessible' bucket from their counts. Id order, one commit per batch."""
    from scanner.scan import commit_with_retry  # local import: scanner imports services

    ids = [row.id for row in db.session.query(Report.id).order_by(Report.id).all()]
    result = {'checked': 0, 'rewritten': 0, 'dry_run': dry_run}
    for start in range(0, len(ids), batch_size):
        chunk = ids[start:start + batch_size]
        rows = db.session.query(Report.id, Report.report, Report.report_counts).filter(Report.id.in_(chunk)).all()
        for row in rows:
            result['checked'] += 1
            report = row.report or {}
            counts = dict(row.report_counts or {})
            needs_slim = any(
                'nodes' in rule for key in ('passes', 'inapplicable') for rule in (report.get(key) or [])
            )
            needs_counts = 'inaccessible' in counts
            if not (needs_slim or needs_counts):
                continue
            result['rewritten'] += 1
            if dry_run:
                continue
            values = {}
            if needs_slim:
                values['report'] = slim_axe_report(report)
            if needs_counts:
                counts.pop('inaccessible', None)
                values['report_counts'] = counts
            db.session.execute(update(Report.__table__).where(Report.id == row.id).values(**values))
        if not dry_run:
            commit_with_retry()
        db.session.expunge_all()
        if log:
            log(f"checked {min(start + batch_size, len(ids))}/{len(ids)} reports, {result['rewritten']} to rewrite")
    return result

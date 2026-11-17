"""Deadlines for findings and the exceptions that suspend them.

Every open finding is due a number of days after it was first seen, by impact (Settings
sla_<impact>_days; 0 means no deadline). A finding is overdue when it is open, in its
page's latest report, past due, and no active exception covers it
(models.compliance.ComplianceException).
"""
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from models import db
from models.compliance import ComplianceException, ManualReview
from models.finding import Finding
from models.settings import Settings
from models.website import Site, Site_Website_Assoc

IMPACTS = ('critical', 'serious', 'moderate', 'minor')
DUE_SOON_DAYS = 14


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def sla_days() -> dict:
    """``{impact: days}``; 0 means findings of that impact have no deadline."""
    out = {}
    for impact in IMPACTS:
        try:
            out[impact] = max(0, int(Settings.get(f'sla_{impact}_days')))
        except (TypeError, ValueError):
            out[impact] = 0
    return out


def due_at(first_seen: datetime | None, impact: str | None, sla: dict) -> datetime | None:
    days = sla.get(impact or '', 0)
    if not first_seen or not days:
        return None
    return first_seen + timedelta(days=days)


def exceptions_by_site(site_ids, today: date | None = None) -> dict:
    """``{site_id: [active exceptions of the websites the page belongs to]}``."""
    site_ids = list(site_ids)
    if not site_ids:
        return {}
    pairs = (db.session.query(Site_Website_Assoc.c.site_id, Site_Website_Assoc.c.website_id)
             .filter(Site_Website_Assoc.c.site_id.in_(site_ids)).all())
    website_ids = {website_id for _, website_id in pairs}
    if not website_ids:
        return {}
    active = [exc for exc in db.session.query(ComplianceException)
              .filter(ComplianceException.website_id.in_(website_ids), ComplianceException.status == 'approved').all()
              if exc.is_active(today)]
    by_website = defaultdict(list)
    for exc in active:
        by_website[exc.website_id].append(exc)
    out = defaultdict(list)
    for site_id, website_id in pairs:
        out[site_id].extend(by_website.get(website_id, []))
    return out


def covering_exception(exceptions: list, rule_id: str, url: str):
    return next((exc for exc in exceptions if exc.covers(rule_id, url)), None)


def deadline_info(rule_id: str, impact: str | None, first_seen: datetime | None, status: str, url: str,
                  exceptions: list, sla: dict, now: datetime) -> dict:
    """``{'due_at', 'overdue', 'exception_id'}`` for one finding."""
    exc = covering_exception(exceptions, rule_id, url)
    due = due_at(first_seen, impact, sla) if status == 'open' else None
    return {
        'due_at': due.strftime("%Y-%m-%dT%H:%M:%SZ") if due else None,
        'overdue': bool(due and due < now and exc is None),
        'exception_id': exc.id if exc else None,
    }


def current_open_findings(site_ids) -> list:
    """Open findings in their page's latest report: rows of (site_id, rule_id, impact,
    first_seen, url)."""
    from services.findings import latest_report_ids  # local import: findings imports models only
    latest = latest_report_ids(list(site_ids))
    if not latest:
        return []
    return (db.session.query(Finding.site_id, Finding.rule_id, Finding.impact, Finding.first_seen, Site.url)
            .join(Site, Site.id == Finding.site_id)
            .filter(Finding.site_id.in_(list(latest)), Finding.last_report_id.in_(list(latest.values())),
                    Finding.status == 'open').all())


def compliance_counts(website_ids, now: datetime | None = None) -> dict:
    """Per website: open findings past their deadline, due within DUE_SOON_DAYS, and
    covered by an exception; active exceptions; the last completed manual review."""
    website_ids = list(website_ids)
    now = now or _utcnow()
    out = {website_id: {'overdue': 0, 'due_soon': 0, 'excepted': 0, 'active_exceptions': 0,
                        'pending_exceptions': 0, 'last_review': None}
           for website_id in website_ids}
    if not website_ids:
        return out
    pairs = (db.session.query(Site_Website_Assoc.c.site_id, Site_Website_Assoc.c.website_id)
             .filter(Site_Website_Assoc.c.website_id.in_(website_ids)).all())
    websites_of = defaultdict(list)
    for site_id, website_id in pairs:
        websites_of[site_id].append(website_id)
    sla = sla_days()
    exceptions = exceptions_by_site(websites_of.keys(), now.date())
    soon = now + timedelta(days=DUE_SOON_DAYS)
    for site_id, rule_id, impact, first_seen, url in current_open_findings(websites_of.keys()):
        exc = covering_exception(exceptions.get(site_id, []), rule_id, url)
        due = due_at(first_seen, impact, sla)
        for website_id in websites_of[site_id]:
            entry = out[website_id]
            if exc is not None:
                entry['excepted'] += 1
            elif due and due < now:
                entry['overdue'] += 1
            elif due and due < soon:
                entry['due_soon'] += 1
    for exc in db.session.query(ComplianceException).filter(ComplianceException.website_id.in_(website_ids)).all():
        if exc.is_active(now.date()):
            out[exc.website_id]['active_exceptions'] += 1
        elif exc.status == 'requested':
            out[exc.website_id]['pending_exceptions'] += 1
    reviews = (db.session.query(ManualReview.website_id, db.func.max(ManualReview.completed_at))
               .filter(ManualReview.website_id.in_(website_ids), ManualReview.status == 'completed')
               .group_by(ManualReview.website_id).all())
    for website_id, completed_at in reviews:
        out[website_id]['last_review'] = completed_at
    return out


def review_interval_days() -> int:
    try:
        return max(1, int(Settings.get('review_interval_days')))
    except (TypeError, ValueError):
        return 365

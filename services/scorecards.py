"""Department scorecards and the compliance report.

compliance_rows gathers, per website, everything an auditor or a manager asks about:
inventory, open issues, deadlines, exceptions, manual reviews, health and the crawl
inventories. department_scorecards rolls those rows up by department. Both are built
from a handful of bulk queries, whatever the number of websites.
"""
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from statistics import median

from sqlalchemy import func

from models import db
from models.finding import SUPPRESSED_STATUSES, Finding
from models.health import HealthCheck, WebsiteHealth
from models.inventory import ThirdPartyHost, Vendor, match_vendor
from models.website import Site_Website_Assoc, Website
from services.compliance import compliance_counts, review_interval_days
from services.findings import latest_report_ids
from services.health import SECURITY_HEADERS
from services.inventory import media_counts, page_content_counts
from services.overview import build_overview, iso

UNASSIGNED = 'No department'
FIX_WINDOW_DAYS = 365

# CSV columns of the compliance report, in order.
REPORT_COLUMNS = (
    'url', 'department', 'business_owner', 'admin', 'lifecycle_status', 'criticality', 'audience',
    'last_scanned', 'pages', 'critical', 'serious', 'moderate', 'minor', 'suppressed', 'overdue', 'due_soon',
    'excepted', 'active_exceptions', 'pending_exceptions', 'last_review', 'review_due',
    'median_days_to_fix', 'uptime_30d', 'up', 'tls_valid', 'tls_expires_at', 'https_redirect',
    'security_headers', 'platform', 'stale_pages', 'mixed_content_pages', 'media_missing_captions',
    'media_unchecked', 'unregistered_third_parties',
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def fix_days_by_website(website_ids, now: datetime) -> dict:
    """``{website_id: [days from first seen to fixed]}`` for findings fixed in the last
    FIX_WINDOW_DAYS."""
    if not website_ids:
        return {}
    rows = (db.session.query(Site_Website_Assoc.c.website_id, Finding.first_seen, Finding.status_at)
            .join(Finding, Finding.site_id == Site_Website_Assoc.c.site_id)
            .filter(Site_Website_Assoc.c.website_id.in_(list(website_ids)), Finding.status == 'fixed',
                    Finding.status_at >= now - timedelta(days=FIX_WINDOW_DAYS))
            .all())
    out = defaultdict(list)
    for website_id, first_seen, fixed_at in rows:
        if first_seen and fixed_at and fixed_at >= first_seen:
            out[website_id].append((fixed_at - first_seen).total_seconds() / 86400)
    return out


def suppressed_by_website(website_ids) -> dict:
    """``{website_id: elements in each page's latest report marked false positive or
    accepted}``: what the website's counts leave out, shown beside them."""
    if not website_ids:
        return {}
    rows = (db.session.query(Site_Website_Assoc.c.website_id, Finding.site_id, Finding.last_report_id)
            .join(Finding, Finding.site_id == Site_Website_Assoc.c.site_id)
            .filter(Site_Website_Assoc.c.website_id.in_(list(website_ids)),
                    Finding.status.in_(SUPPRESSED_STATUSES))
            .all())
    latest = latest_report_ids({site_id for _, site_id, _ in rows})
    out = defaultdict(int)
    for website_id, site_id, report_id in rows:
        if report_id is not None and report_id == latest.get(site_id):
            out[website_id] += 1
    return out


def uptime_by_website(website_ids, now: datetime, days: int = 30) -> dict:
    """``{website_id: percent of checks up over the last ``days``}``."""
    if not website_ids:
        return {}
    rows = (db.session.query(HealthCheck.website_id, func.count(), func.sum(func.cast(HealthCheck.up, db.Integer)))
            .filter(HealthCheck.website_id.in_(list(website_ids)), HealthCheck.checked_at >= now - timedelta(days=days))
            .group_by(HealthCheck.website_id).all())
    return {website_id: round(100 * (up or 0) / total, 2) for website_id, total, up in rows if total}


def unregistered_third_parties(website_ids) -> dict:
    """``{website_id: third-party hosts that match no vendor}``."""
    vendors = db.session.query(Vendor).all()
    out = defaultdict(int)
    for website_id, host in (db.session.query(ThirdPartyHost.website_id, ThirdPartyHost.host)
                             .filter(ThirdPartyHost.website_id.in_(list(website_ids))).all()):
        if match_vendor(host, vendors) is None:
            out[website_id] += 1
    return out


def compliance_rows(websites, now: datetime | None = None) -> list:
    """One row per website (see REPORT_COLUMNS, plus id and fix_days for roll-ups)."""
    now = now or _utcnow()
    websites = list(websites)
    ids = [website.id for website in websites]
    if not ids:
        return []
    overview = {row['id']: row for row in build_overview(websites, top=0)['websites']}
    compliance = compliance_counts(ids, now)
    fix_days = fix_days_by_website(ids, now)
    suppressed = suppressed_by_website(ids)
    uptime = uptime_by_website(ids, now)
    health = {row.website_id: row for row in db.session.query(WebsiteHealth).filter(WebsiteHealth.website_id.in_(ids)).all()}
    media = media_counts(ids)
    content = page_content_counts(ids, now)
    third = unregistered_third_parties(ids)
    interval = timedelta(days=review_interval_days())

    rows = []
    for website in websites:
        violations = overview[website.id]['violations']
        c = compliance[website.id]
        h = health.get(website.id)
        last_review = c['last_review']
        days = fix_days.get(website.id, [])
        rows.append({
            'id': website.id,
            'url': website.url,
            'department': website.department or None,
            'business_owner': website.business_owner,
            'admin': website.admin.username if website.admin else None,
            'lifecycle_status': website.lifecycle_status or 'live',
            'criticality': website.criticality,
            'audience': website.audience,
            'last_scanned': iso(website.last_scanned),
            'pages': overview[website.id]['pages'],
            'critical': violations['critical'],
            'serious': violations['serious'],
            'moderate': violations['moderate'],
            'minor': violations['minor'],
            'suppressed': suppressed.get(website.id, 0),
            'overdue': c['overdue'],
            'due_soon': c['due_soon'],
            'excepted': c['excepted'],
            'active_exceptions': c['active_exceptions'],
            'pending_exceptions': c['pending_exceptions'],
            'last_review': iso(last_review),
            'review_due': last_review is None or now - last_review > interval,
            'median_days_to_fix': round(median(days), 1) if days else None,
            'fix_days': days,
            'uptime_30d': uptime.get(website.id),
            'up': h.up if h else None,
            'tls_valid': h.tls_valid if h else None,
            'tls_expires_at': iso(h.tls_expires_at) if h else None,
            'https_redirect': h.https_redirect if h else None,
            'security_headers': (sum(1 for name in SECURITY_HEADERS if (h.security_headers or {}).get(name))
                                 if h and h.security_headers else None),
            'platform': ' '.join(filter(None, (h.platform, h.platform_version))) if h and h.platform else None,
            'stale_pages': content[website.id]['stale_pages'],
            'mixed_content_pages': content[website.id]['mixed_content_pages'],
            'media_missing_captions': media[website.id]['missing'],
            'media_unchecked': media[website.id]['unknown'],
            'unregistered_third_parties': third.get(website.id, 0),
        })
    return rows


def _percent(part: int, whole: int) -> float | None:
    return round(100 * part / whole, 1) if whole else None


def department_scorecards(rows: list) -> list:
    """Roll compliance rows up by department (retired websites left out), worst first:
    most overdue issues, then most critical and serious ones."""
    groups = defaultdict(list)
    for row in rows:
        if row['lifecycle_status'] == 'retired':
            continue
        groups[row['department'] or UNASSIGNED].append(row)
    cards = []
    for department, members in groups.items():
        audited = [row for row in members if row['last_scanned']]
        uptimes = [row['uptime_30d'] for row in members if row['uptime_30d'] is not None]
        fix_days = [d for row in members for d in row['fix_days']]
        cards.append({
            'department': department,
            'websites': len(members),
            'audited': len(audited),
            'pages': sum(row['pages'] for row in members),
            'critical': sum(row['critical'] for row in members),
            'serious': sum(row['serious'] for row in members),
            'moderate': sum(row['moderate'] for row in members),
            'minor': sum(row['minor'] for row in members),
            'suppressed': sum(row['suppressed'] for row in members),
            'overdue': sum(row['overdue'] for row in members),
            'due_soon': sum(row['due_soon'] for row in members),
            'active_exceptions': sum(row['active_exceptions'] for row in members),
            'clean_percent': _percent(sum(1 for row in audited if not row['critical'] and not row['serious']), len(audited)),
            'reviewed_percent': _percent(sum(1 for row in members if not row['review_due']), len(members)),
            'median_days_to_fix': round(median(fix_days), 1) if fix_days else None,
            'uptime_30d': round(sum(uptimes) / len(uptimes), 2) if uptimes else None,
            'down': sum(1 for row in members if row['up'] is False),
            'tls_problems': sum(1 for row in members if row['tls_valid'] is False),
            'stale_pages': sum(row['stale_pages'] for row in members),
            'mixed_content_pages': sum(row['mixed_content_pages'] for row in members),
            'media_missing_captions': sum(row['media_missing_captions'] for row in members),
            'website_ids': [row['id'] for row in members],
        })
    cards.sort(key=lambda c: (-c['overdue'], -(c['critical'] + c['serious']), c['department']))
    return cards


def report_websites(user, department: str | None = None, include_retired: bool = False):
    """The websites ``user`` may view, for the report: optionally one department
    (UNASSIGNED selects websites without one)."""
    query = db.session.query(Website).filter(Website.visible_to(user)).order_by(Website.url)
    if department == UNASSIGNED:
        query = query.filter((Website.department.is_(None)) | (Website.department == ''))
    elif department:
        query = query.filter(Website.department == department)
    if not include_retired:
        query = query.filter(Website.lifecycle_status != 'retired')
    return query.all()

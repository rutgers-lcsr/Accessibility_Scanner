"""Aggregations over the latest report of every page.

Shared by the system dashboard, the notification emails and the weekly digest, so all
three describe a website the same way. Everything here reads the light report columns
only (never the report JSON or the screenshot), except top_rules, which has to read
the violation lists.
"""
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import joinedload, selectinload

from models import db
from models.report import Report
from models.website import Site, Site_Website_Assoc, Website
from services.documents import document_counts, empty_document_counts
from models.notifications import WebsiteView
from services.findings import triage_activity
from services.history import effective_counts, sum_counts

IMPACT_ORDER = {'critical': 0, 'serious': 1, 'moderate': 2, 'minor': 3}
_CHUNK = 500  # ids per IN (...) when loading report JSON


def iso(value: datetime | None) -> str | None:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ") if value else None


def latest_reports(website_ids, before: datetime | None = None) -> dict:
    """The most recent report of every page under the given websites.

    With ``before``, the most recent report at that moment instead, which is how the
    emails and the digest describe "then" versus "now". Returns ``{site_id: row}``
    where row has id, site_id, url, timestamp and report_counts.
    """
    if not website_ids:
        return {}
    latest_ts = (
        db.session.query(Report.site_id, func.max(Report.timestamp).label('ts'))
        .join(Site_Website_Assoc, Site_Website_Assoc.c.site_id == Report.site_id)
        .filter(Site_Website_Assoc.c.website_id.in_(website_ids))
    )
    if before is not None:
        latest_ts = latest_ts.filter(Report.timestamp <= before)
    latest_ts = latest_ts.group_by(Report.site_id).subquery()
    rows = (
        db.session.query(Report.id, Report.site_id, Report.url, Report.timestamp, Report.report_counts, Report.suppressed_counts)
        .join(latest_ts, (latest_ts.c.site_id == Report.site_id) & (latest_ts.c.ts == Report.timestamp))
        .all()
    )
    by_site = {}
    for row in rows:
        # Two reports can share a page's max timestamp; keep the newest id.
        if row.site_id not in by_site or row.id > by_site[row.site_id].id:
            by_site[row.site_id] = row
    return by_site


def reports_at_last_email(website_ids) -> dict:
    """``{website_id: {site_id: row}}``: the report every page had when the website's
    people were last emailed (Website.last_notified), the per-website form of
    ``latest_reports(..., before=...)``. Websites never emailed are absent."""
    if not website_ids:
        return {}
    then_ts = (
        db.session.query(
            Site_Website_Assoc.c.website_id.label('website_id'),
            Report.site_id.label('site_id'),
            func.max(Report.timestamp).label('ts'),
        )
        .join(Site_Website_Assoc, Site_Website_Assoc.c.site_id == Report.site_id)
        .join(Website, Website.id == Site_Website_Assoc.c.website_id)
        .filter(Site_Website_Assoc.c.website_id.in_(website_ids), Report.timestamp <= Website.last_notified)
        .group_by(Site_Website_Assoc.c.website_id, Report.site_id)
        .subquery()
    )
    rows = (
        db.session.query(then_ts.c.website_id, Report.id, Report.site_id, Report.timestamp, Report.report_counts, Report.suppressed_counts)
        .join(then_ts, (then_ts.c.site_id == Report.site_id) & (then_ts.c.ts == Report.timestamp))
        .all()
    )
    by_website = defaultdict(dict)
    for row in rows:
        # Two reports can share a page's max timestamp; keep the newest id.
        kept = by_website[row.website_id].get(row.site_id)
        if kept is None or row.id > kept.id:
            by_website[row.website_id][row.site_id] = row
    return by_website


def sites_of(website_ids) -> dict:
    """``{website_id: {site_id, ...}}`` for the given websites."""
    result = defaultdict(set)
    if not website_ids:
        return result
    assoc = (
        db.session.query(Site_Website_Assoc.c.site_id, Site_Website_Assoc.c.website_id)
        .filter(Site_Website_Assoc.c.website_id.in_(website_ids))
        .all()
    )
    for site_id, website_id in assoc:
        result[website_id].add(site_id)
    return result


def top_rules(report_ids, limit) -> list:
    """The most widespread violations across the given reports.

    Ranked most severe first, then by pages affected, then by occurrences (nodes).
    Elements whose finding is suppressed (services.findings) are left out. This is the
    only aggregation that reads the full report JSON.
    """
    from services.findings import suppressed_fingerprints, fingerprint, normalise_selector

    stats = {}
    ids = list(report_ids)
    for start in range(0, len(ids), _CHUNK):
        chunk = ids[start:start + _CHUNK]
        query = db.session.query(Report.id, Report.site_id, Report.report).filter(Report.id.in_(chunk))
        rows = query.all()
        suppressed = suppressed_fingerprints({row.site_id for row in rows})
        for _, site_id, report in rows:
            for rule in (report or {}).get('violations') or []:
                rule_id = rule.get('id')
                if not rule_id:
                    continue
                nodes = [
                    node for node in (rule.get('nodes') or [])
                    if (site_id, fingerprint(rule_id, normalise_selector(node.get('target')))) not in suppressed
                ]
                if rule.get('nodes') and not nodes:
                    continue  # every element on this page is suppressed
                entry = stats.setdefault(rule_id, {
                    'id': rule_id,
                    'impact': rule.get('impact'),
                    'help': rule.get('help'),
                    'help_url': rule.get('helpUrl'),
                    'description': rule.get('description'),
                    'pages': 0,
                    'occurrences': 0,
                })
                entry['pages'] += 1
                entry['occurrences'] += len(nodes)
    ranked = sorted(
        stats.values(),
        key=lambda r: (IMPACT_ORDER.get(r['impact'], len(IMPACT_ORDER)), -r['pages'], -r['occurrences']),
    )
    return ranked[:limit]


def website_row(website: Website, site_ids: set, latest_by_site: dict, documents: dict | None = None) -> dict:
    counts = sum_counts({
        site_id: effective_counts(latest_by_site[site_id].report_counts, latest_by_site[site_id].suppressed_counts)
        for site_id in site_ids if site_id in latest_by_site
    })
    return {
        'id': website.id,
        'url': website.url,
        'categories': website.get_categories(),
        'pages': len(site_ids),
        'pages_audited': sum(1 for site_id in site_ids if site_id in latest_by_site),
        'last_scanned': iso(website.last_scanned),
        'last_scan_status': website.last_scan_status,
        'violations': counts['violations'],
        'passes': counts['passes']['total'],
        'incomplete': counts['incomplete']['total'],
        'documents': (documents or {}).get('total', 0),
        'untagged_pdfs': (documents or {}).get('untagged_pdf', 0),
    }


def scan_status_counts(websites) -> Counter:
    counts = Counter()
    for website in websites:
        counts[website.last_scan_status or ('never' if website.last_scanned is None else 'unknown')] += 1
    return counts


def build_overview(websites, top: int = 10) -> dict:
    """Totals, one row per website (worst first) and the top violations, over the
    latest report of every page. ``latest_by_site`` and ``sites_of`` are returned too
    so callers can go on to compute history or details without re-querying."""
    website_ids = [website.id for website in websites]
    site_ids_of = sites_of(website_ids)
    latest_by_site = latest_reports(website_ids)

    # A page may belong to several websites; it is counted once in the totals and
    # once per website in the rows.
    all_site_ids = set().union(*site_ids_of.values()) if site_ids_of else set()
    totals = sum_counts({
        site_id: effective_counts(row.report_counts, row.suppressed_counts)
        for site_id, row in latest_by_site.items()
    })
    last_scan = max((row.timestamp for row in latest_by_site.values()), default=None)

    documents = document_counts(website_ids)
    rows = [website_row(website, site_ids_of[website.id], latest_by_site, documents.get(website.id)) for website in websites]
    rows.sort(key=lambda row: (-row['violations']['total'], row['url']))

    return {
        'totals': {
            'websites': len(websites),
            'pages': len(all_site_ids),
            'pages_audited': len(latest_by_site),
            'last_scan': iso(last_scan),
            'violations': totals['violations'],
            'passes': totals['passes']['total'],
            'incomplete': totals['incomplete']['total'],
            'scan_status': dict(scan_status_counts(websites)),
            'documents': sum(row['documents'] for row in rows),
            'untagged_pdfs': sum(row['untagged_pdfs'] for row in rows),
        },
        'websites': rows,
        'top_rules': top_rules([row.id for row in latest_by_site.values()], top) if top else [],
        'latest_by_site': latest_by_site,
        'sites_of': site_ids_of,
    }


def build_digest(days: int = 7) -> dict:
    """The weekly system digest for site admins: totals now, the websites that moved most
    since ``days`` ago, websites audited for the first time, failing and never-scanned
    websites, websites added, and the top rules. Plain data, ready for a template."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    cutoff = now - timedelta(days=days)
    websites = db.session.query(Website).order_by(Website.url).all()
    overview = build_overview(websites, top=10)
    then = latest_reports([website.id for website in websites], before=cutoff)
    latest = overview['latest_by_site']
    sites_of = overview['sites_of']
    row_of = {row['id']: row for row in overview['websites']}

    movers, newly_audited = [], []
    for website in websites:
        site_ids = sites_of.get(website.id, set())
        current = row_of[website.id]['violations']['total']
        then_rows = {site_id: then[site_id] for site_id in site_ids if site_id in then}
        if then_rows:
            previous = sum_counts({
                site_id: effective_counts(row.report_counts, row.suppressed_counts)
                for site_id, row in then_rows.items()
            })['violations']['total']
            if current != previous:
                movers.append({'id': website.id, 'url': website.url, 'previous': previous,
                               'current': current, 'delta': current - previous})
        elif any(site_id in latest for site_id in site_ids):
            newly_audited.append({'id': website.id, 'url': website.url, 'violations': current})

    return {
        'period': {'days': days, 'since': iso(cutoff), 'until': iso(now)},
        'websites_count': len(websites),
        'totals': overview['totals'],
        'top_rules': overview['top_rules'],
        'movers_up': sorted((m for m in movers if m['delta'] > 0), key=lambda m: (-m['delta'], m['url']))[:5],
        'movers_down': sorted((m for m in movers if m['delta'] < 0), key=lambda m: (m['delta'], m['url']))[:5],
        'newly_audited': newly_audited,
        'failing': [
            {'id': w.id, 'url': w.url, 'status': w.last_scan_status, 'error': w.last_scan_error, 'last_scanned': iso(w.last_scanned)}
            for w in websites if w.last_scan_status in ('failed', 'unreachable')
        ],
        'never_scanned': [
            {'id': w.id, 'url': w.url, 'active': bool(w.active), 'created_at': iso(w.created_at)}
            for w in websites if w.last_scanned is None
        ],
        'scanned_this_period': sum(1 for w in websites if w.last_scanned and w.last_scanned >= cutoff),
        'new_websites': [
            {'id': w.id, 'url': w.url, 'admin': w.admin.username if w.admin else None}
            for w in websites if w.created_at and w.created_at >= cutoff
        ],
    }


VIOLATION_KEYS = ('total', 'critical', 'serious', 'moderate', 'minor')


def _violations_total(rows) -> int | None:
    """Effective open violations over ``{site_id: report row}``; None without rows."""
    if not rows:
        return None
    return sum_counts({
        site_id: effective_counts(row.report_counts, row.suppressed_counts)
        for site_id, row in rows.items()
    })['violations']['total']


def _add_change(total: dict | None, change: dict | None) -> dict | None:
    """Sum a website's before/after pair into its owner's, over websites that have one."""
    if change is None:
        return total
    if total is None:
        return {'previous': change['previous'], 'current': change['current']}
    total['previous'] += change['previous']
    total['current'] += change['current']
    return total


def build_owners(days: int = 90) -> dict:
    """Every website grouped by its admin user, worst first, for the admin Owners page:
    effective counts now, the change since the website's people were last emailed and
    since ``days`` ago, and how many findings a person has triaged. Websites without an
    admin form one "unassigned" owner (username None)."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    cutoff = now - timedelta(days=days)
    websites = (
        db.session.query(Website)
        .options(joinedload(Website.admin), selectinload(Website.users))
        .order_by(Website.url)
        .all()
    )
    website_ids = [website.id for website in websites]
    overview = build_overview(websites, top=0)
    row_of = {row['id']: row for row in overview['websites']}
    sites_of_website = overview['sites_of']
    activity = triage_activity(website_ids)
    at_email = reports_at_last_email(website_ids)
    at_period = latest_reports(website_ids, before=cutoff)
    views = WebsiteView.by_website(website_ids)

    owners = {}
    for website in websites:
        row = row_of[website.id]
        site_ids = sites_of_website.get(website.id, set())
        current = row['violations']['total']
        previous_email = _violations_total(at_email.get(website.id, {}))
        previous_period = _violations_total({site_id: at_period[site_id] for site_id in site_ids if site_id in at_period})
        triage = activity.get(website.id, {'triaged': 0, 'last_triage': None})
        row.update({
            'description': website.description,
            'users': [user.username for user in website.users],
            'active': bool(website.active),
            'should_email': bool(website.should_email),
            'last_notified': iso(website.last_notified),
            'activity': {'triaged': triage['triaged'], 'last_triage': iso(triage['last_triage'])},
            'since_last_email': None if previous_email is None else
                {'when': iso(website.last_notified), 'previous': previous_email, 'current': current},
            'since_period': None if previous_period is None else {'previous': previous_period, 'current': current},
            'last_viewed': iso(max(views.get(website.id, {}).values(), default=None)),
            'reminders': {
                'attention_since': iso(website.attention_since),
                'last_reminded_at': iso(website.last_reminded_at),
                'count': website.reminder_count or 0,
                'escalated_at': iso(website.escalated_at),
            },
        })

        owner = owners.get(website.admin_id)
        if owner is None:
            admin = website.admin
            owner = owners[website.admin_id] = {
                'id': admin.id if admin else None,
                'username': admin.username if admin else None,
                'email': admin.email if admin else None,
                'last_login': iso(admin.last_login) if admin else None,
                'last_viewed': None,
                'websites_count': 0,
                'pages': 0,
                'pages_audited': 0,
                'violations': {key: 0 for key in VIOLATION_KEYS},
                'last_scanned': None,
                'last_notified': None,
                'activity': {'triaged': 0, 'last_triage': None},
                'since_last_email': None,
                'since_period': None,
                'websites': [],
            }
        owner['websites'].append(row)
        owner['websites_count'] += 1
        owner['pages'] += row['pages']
        owner['pages_audited'] += row['pages_audited']
        for key in VIOLATION_KEYS:
            owner['violations'][key] += row['violations'][key]
        # ISO strings of one format order like the moments they name.
        owner['last_scanned'] = max(filter(None, (owner['last_scanned'], row['last_scanned'])), default=None)
        owner['last_notified'] = max(filter(None, (owner['last_notified'], row['last_notified'])), default=None)
        owner['last_viewed'] = max(filter(None, (owner['last_viewed'], row['last_viewed'])), default=None)
        owner['activity']['triaged'] += row['activity']['triaged']
        owner['activity']['last_triage'] = max(
            filter(None, (owner['activity']['last_triage'], row['activity']['last_triage'])), default=None)
        owner['since_last_email'] = _add_change(owner['since_last_email'], row['since_last_email'])
        owner['since_period'] = _add_change(owner['since_period'], row['since_period'])

    for owner in owners.values():
        owner['websites'].sort(key=lambda row: (-row['violations']['total'], row['url']))
    return {
        'generated_at': iso(now),
        'period': {'days': days, 'since': iso(cutoff)},
        'owners': sorted(owners.values(), key=lambda owner: (-owner['violations']['total'], owner['username'] or '')),
    }

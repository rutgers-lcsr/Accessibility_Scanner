"""Aggregations over the latest report of every page.

Shared by the system dashboard, the notification emails and the weekly digest, so all
three describe a website the same way. Everything here reads the light report columns
only (never the report JSON or the screenshot), except top_rules, which has to read
the violation lists.
"""
from collections import Counter, defaultdict
from datetime import datetime

from sqlalchemy import func

from models import db
from models.report import Report
from models.website import Site_Website_Assoc, Website
from services.history import sum_counts

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
        db.session.query(Report.id, Report.site_id, Report.url, Report.timestamp, Report.report_counts)
        .join(latest_ts, (latest_ts.c.site_id == Report.site_id) & (latest_ts.c.ts == Report.timestamp))
        .all()
    )
    by_site = {}
    for row in rows:
        # Two reports can share a page's max timestamp; keep the newest id.
        if row.site_id not in by_site or row.id > by_site[row.site_id].id:
            by_site[row.site_id] = row
    return by_site


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
    This is the only aggregation that reads the full report JSON.
    """
    stats = {}
    ids = list(report_ids)
    for start in range(0, len(ids), _CHUNK):
        chunk = ids[start:start + _CHUNK]
        query = db.session.query(Report.id, Report.report).filter(Report.id.in_(chunk))
        for _, report in query.all():
            for rule in (report or {}).get('violations') or []:
                rule_id = rule.get('id')
                if not rule_id:
                    continue
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
                entry['occurrences'] += len(rule.get('nodes') or [])
    ranked = sorted(
        stats.values(),
        key=lambda r: (IMPACT_ORDER.get(r['impact'], len(IMPACT_ORDER)), -r['pages'], -r['occurrences']),
    )
    return ranked[:limit]


def website_row(website: Website, site_ids: set, latest_by_site: dict) -> dict:
    counts = sum_counts({
        site_id: latest_by_site[site_id].report_counts
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
    totals = sum_counts({site_id: row.report_counts for site_id, row in latest_by_site.items()})
    last_scan = max((row.timestamp for row in latest_by_site.values()), default=None)

    rows = [website_row(website, site_ids_of[website.id], latest_by_site) for website in websites]
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
        },
        'websites': rows,
        'top_rules': top_rules([row.id for row in latest_by_site.values()], top),
        'latest_by_site': latest_by_site,
        'sites_of': site_ids_of,
    }

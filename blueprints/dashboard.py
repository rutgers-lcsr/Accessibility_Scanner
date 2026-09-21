"""System-wide accessibility overview.

One payload with everything the dashboard page needs, scoped to the websites the caller
may view (Website.visible_to): site admins see the whole system, everyone else the
websites they administer, belong to, or that are public.
"""
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import current_user, jwt_required
from sqlalchemy import func

from models import db
from models.report import Report
from models.website import Site_Website_Assoc, Website
from services.history import daily_history, sum_counts

dashboard_bp = Blueprint('dashboard', __name__)

IMPACT_ORDER = {'critical': 0, 'serious': 1, 'moderate': 2, 'minor': 3}
DEFAULT_DAYS = 90
DEFAULT_TOP_RULES = 10
_CHUNK = 500  # ids per IN (...) when loading report JSON


def _clamp(value, low, high, default):
    if value is None:
        return default
    return max(low, min(high, value))


def _iso(value: datetime | None) -> str | None:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ") if value else None


def _latest_reports(website_ids):
    """The most recent report of every page under the given websites.

    Returns ``{site_id: row}`` where row has id, site_id, timestamp and report_counts.
    Only the light columns are loaded; the report JSON and screenshot are not.
    """
    latest_ts = (
        db.session.query(Report.site_id, func.max(Report.timestamp).label('ts'))
        .join(Site_Website_Assoc, Site_Website_Assoc.c.site_id == Report.site_id)
        .filter(Site_Website_Assoc.c.website_id.in_(website_ids))
        .group_by(Report.site_id)
        .subquery()
    )
    rows = (
        db.session.query(Report.id, Report.site_id, Report.timestamp, Report.report_counts)
        .join(latest_ts, (latest_ts.c.site_id == Report.site_id) & (latest_ts.c.ts == Report.timestamp))
        .all()
    )
    by_site = {}
    for row in rows:
        # Two reports can share a page's max timestamp; keep the newest id.
        if row.site_id not in by_site or row.id > by_site[row.site_id].id:
            by_site[row.site_id] = row
    return by_site


def _top_rules(report_ids, limit):
    """The most widespread violations across the given reports.

    Ranked most severe first, then by pages affected, then by occurrences (nodes).
    This is the only part that reads the full report JSON.
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


def _website_row(website: Website, site_ids: set, latest_by_site: dict) -> dict:
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
        'last_scanned': _iso(website.last_scanned),
        'last_scan_status': website.last_scan_status,
        'violations': counts['violations'],
        'passes': counts['passes']['total'],
        'incomplete': counts['incomplete']['total'],
    }


@dashboard_bp.route('/', methods=['GET'])
@jwt_required()
def get_dashboard():
    """
    System-wide accessibility overview for the websites the caller may view.
    ---
    tags:
        - Dashboard
    parameters:
        - in: query
          name: days
          type: integer
          required: false
          default: 90
          description: How many days of history to return (1-730).
        - in: query
          name: top
          type: integer
          required: false
          default: 10
          description: How many of the most common violations to return (1-50).
    responses:
        200:
            description: Totals, per-website and per-category rows, top violations, and daily history.
        401:
            description: Not logged in.
    """
    days = _clamp(request.args.get('days', type=int), 1, 730, DEFAULT_DAYS)
    top = _clamp(request.args.get('top', type=int), 1, 50, DEFAULT_TOP_RULES)

    websites = db.session.query(Website).filter(Website.visible_to(current_user)).all()
    website_ids = [website.id for website in websites]

    # A page may belong to several websites; it is counted once in the system totals
    # and once per website in the per-website rows.
    sites_of = defaultdict(set)
    if website_ids:
        assoc = (
            db.session.query(Site_Website_Assoc.c.site_id, Site_Website_Assoc.c.website_id)
            .filter(Site_Website_Assoc.c.website_id.in_(website_ids))
            .all()
        )
        for site_id, website_id in assoc:
            sites_of[website_id].add(site_id)
    all_site_ids = set().union(*sites_of.values()) if sites_of else set()

    latest_by_site = _latest_reports(website_ids) if website_ids else {}
    totals = sum_counts({site_id: row.report_counts for site_id, row in latest_by_site.items()})
    last_scan = max((row.timestamp for row in latest_by_site.values()), default=None)

    website_rows = [_website_row(website, sites_of[website.id], latest_by_site) for website in websites]
    website_rows.sort(key=lambda row: (-row['violations']['total'], row['url']))

    scan_status = Counter()
    for website in websites:
        scan_status[website.last_scan_status or ('never' if website.last_scanned is None else 'unknown')] += 1

    categories = {}
    for row in website_rows:
        for name in row['categories'] or ['Uncategorized']:
            bucket = categories.setdefault(name, {
                'category': name,
                'websites': 0,
                'pages': 0,
                'violations': {key: 0 for key in ('total', 'critical', 'serious', 'moderate', 'minor')},
                'passes': 0,
            })
            bucket['websites'] += 1
            bucket['pages'] += row['pages']
            bucket['passes'] += row['passes']
            for key in bucket['violations']:
                bucket['violations'][key] += row['violations'][key]
    category_rows = sorted(categories.values(), key=lambda c: (-c['violations']['total'], c['category']))

    top_rules = _top_rules([row.id for row in latest_by_site.values()], top)

    history = []
    if website_ids:
        rows = (
            db.session.query(Report.site_id, Report.timestamp, Report.report_counts)
            .join(Site_Website_Assoc, Site_Website_Assoc.c.site_id == Report.site_id)
            .filter(Site_Website_Assoc.c.website_id.in_(website_ids))
            .order_by(Report.timestamp.asc())
            .all()
        )
        since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
        history = [point for point in daily_history(rows) if point['date'] >= since]

    return jsonify({
        'generated_at': _iso(datetime.now(timezone.utc)),
        'days': days,
        'totals': {
            'websites': len(websites),
            'pages': len(all_site_ids),
            'pages_audited': len(latest_by_site),
            'last_scan': _iso(last_scan),
            'violations': totals['violations'],
            'passes': totals['passes']['total'],
            'incomplete': totals['incomplete']['total'],
            'scan_status': dict(scan_status),
        },
        'websites': website_rows,
        'categories': category_rows,
        'top_rules': top_rules,
        'history': history,
    }), 200

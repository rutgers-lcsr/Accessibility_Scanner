"""System-wide accessibility overview.

One payload with everything the dashboard page needs, scoped to the websites the caller
may view (Website.visible_to): site admins see the whole system, everyone else the
websites they administer, belong to, or that are public. The aggregation itself lives
in services.overview so the emails and the digest share it.
"""
from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import current_user, jwt_required

from authentication.login import admin_required
from models import db
from models.report import Report
from models.website import Site_Website_Assoc, Website
from services.history import daily_history, effective_counts
from services.overview import build_overview, build_owners, iso
from utils.export import csv_response

dashboard_bp = Blueprint('dashboard', __name__)

DEFAULT_DAYS = 90
DEFAULT_TOP_RULES = 10


def _clamp(value, low, high, default):
    if value is None:
        return default
    return max(low, min(high, value))


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
    overview = build_overview(websites, top=top)

    categories = {}
    for row in overview['websites']:
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

    history = []
    if website_ids:
        rows = (
            db.session.query(Report.site_id, Report.timestamp, Report.report_counts, Report.suppressed_counts)
            .join(Site_Website_Assoc, Site_Website_Assoc.c.site_id == Report.site_id)
            .filter(Site_Website_Assoc.c.website_id.in_(website_ids))
            .order_by(Report.timestamp.asc())
            .all()
        )
        since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
        points = daily_history([(site_id, ts, effective_counts(counts, suppressed)) for site_id, ts, counts, suppressed in rows])
        history = [point for point in points if point['date'] >= since]

    return jsonify({
        'generated_at': iso(datetime.now(timezone.utc)),
        'days': days,
        'totals': overview['totals'],
        'websites': overview['websites'],
        'categories': category_rows,
        'top_rules': overview['top_rules'],
        'history': history,
    }), 200


OWNER_CSV_COLUMNS = [
    'owner', 'owner_email', 'website_id', 'url', 'description', 'categories', 'active',
    'pages', 'pages_audited', 'violations', 'critical', 'serious', 'moderate', 'minor',
    'last_scanned', 'last_notified', 'triaged', 'last_triage',
    'violations_at_last_email', 'violations_at_period_start',
]


def _owner_csv_rows(owners):
    """One row per website, with its owner's name and email first."""
    for owner in owners:
        for website in owner['websites']:
            yield [
                owner['username'], owner['email'], website['id'], website['url'], website['description'],
                ', '.join(website['categories']), website['active'],
                website['pages'], website['pages_audited'],
                website['violations']['total'], website['violations']['critical'], website['violations']['serious'],
                website['violations']['moderate'], website['violations']['minor'],
                website['last_scanned'], website['last_notified'],
                website['activity']['triaged'], website['activity']['last_triage'],
                (website['since_last_email'] or {}).get('previous'),
                (website['since_period'] or {}).get('previous'),
            ]


@dashboard_bp.route('/owners/', methods=['GET'])
@admin_required
def get_owners():
    """
    Every website grouped by its admin user, worst first, with each owner's contact
    details, whether the counts moved since their last email and since the period
    start, and how many findings a person has triaged. Site admins only.
    ---
    tags:
        - Dashboard
    parameters:
        - in: query
          name: days
          type: integer
          required: false
          default: 90
          description: The period the "since period start" change covers (1-730).
        - in: query
          name: format
          type: string
          required: false
          description: "csv" for a download with one row per website.
    responses:
        200:
            description: Owners, each with totals and their websites.
        401:
            description: Not logged in.
        403:
            description: Not a site admin.
    """
    days = _clamp(request.args.get('days', type=int), 1, 730, DEFAULT_DAYS)
    owners = build_owners(days)
    if request.args.get('format') == 'csv':
        return csv_response(OWNER_CSV_COLUMNS, _owner_csv_rows(owners['owners']), 'owners.csv')
    return jsonify(owners), 200

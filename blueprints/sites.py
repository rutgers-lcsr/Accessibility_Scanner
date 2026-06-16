from flask import Blueprint, jsonify, request
from flask_jwt_extended import current_user, jwt_required

from models.report import Report
from models.website import Site, Website
from models import db

sites_bp = Blueprint('sites', __name__)

@sites_bp.route('/<int:site_id>/', methods=['GET'])
@jwt_required(optional=True)
def get_site(site_id):
    site = db.session.get(Site, site_id)
    if not site:
        return jsonify({'error': 'Site not found'}), 404

    if current_user:
        if not site.can_view(current_user):
            return jsonify({'error': 'Unauthorized'}), 403

    if not current_user:
        # make sure that non-admin users can only see public websites
        if site.public == False:
            return jsonify({'error': 'Unauthorized'}), 403

    return jsonify(site.to_dict()), 200


@sites_bp.route('/<int:site_id>/history/', methods=['GET'])
@jwt_required(optional=True)
def get_site_history(site_id):
    site = db.session.get(Site, site_id)
    if not site:
        return jsonify({'error': 'Site not found'}), 404

    if current_user:
        if not site.can_view(current_user):
            return jsonify({'error': 'Unauthorized'}), 403

    if not current_user:
        # make sure that non-admin users can only see public websites
        if site.public == False:
            return jsonify({'error': 'Unauthorized'}), 403

    limit = request.args.get('limit', type=int)

    reports_q = (
        site.reports
        .order_by(Report.timestamp.asc())
        .with_entities(Report.id, Report.timestamp, Report.report_counts)
    )
    if limit:
        # Keep the most recent `limit` reports, but still return them oldest->newest
        reports_q = (
            site.reports
            .order_by(Report.timestamp.desc())
            .with_entities(Report.id, Report.timestamp, Report.report_counts)
            .limit(limit)
        )
        reports = list(reversed(reports_q.all()))
    else:
        reports = reports_q.all()

    items = [{
        'id': r.id,
        'timestamp': r.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ") if r.timestamp else None,
        'report_counts': r.report_counts,
    } for r in reports]

    return jsonify({'count': len(items), 'items': items}), 200
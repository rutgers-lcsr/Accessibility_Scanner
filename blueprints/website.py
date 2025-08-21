from flask import Blueprint, jsonify, request
from flask_login import login_required
from authentication.login import user_is_admin
from models.report import AxeReportCounts, Report
from models.website import Domains, Site, Website 
from models import db
from urllib.parse import urlparse

from scanner.accessibility.ace import AxeReportKeys
from sqlalchemy import Integer, cast, func
website_bp = Blueprint('website', __name__,  url_prefix="/websites")


@website_bp.route('/', methods=['POST'])
def create_website():
    data = request.get_json()
    base_url = data.get('base_url')
    if not base_url:
        return jsonify({'error': 'Base URL is required'}), 400
    
    # Check if valid urlparse
    parsed = urlparse(base_url)
    if not all([parsed.scheme, parsed.netloc]):
        return jsonify({'error': 'The provided URL is invalid'}), 400

    base_url = f"{parsed.scheme}://{parsed.netloc}"

    existing_domain = Domains.query.filter(Domains.part_of_domain(base_url)).first()
    if not existing_domain:
        return jsonify({'error': 'Domain not found'}), 404

    if not existing_domain.active:
        return jsonify({'error': 'The domain of the website your requested is not active, please contact the admins if you believe this is a problem'}), 400
    

    new_website = Website(url=base_url)
    
    # send email to user and admin, user confirming and admin to activate

    db.session.add(new_website)
    db.session.commit()
    
    return jsonify(new_website.to_dict()), 201  

@website_bp.route('/', methods=['PATCH'])
@login_required
def update_website():
    data = request.get_json()
    website_id = data.get('id')
    website = db.session.get(Website, website_id)
    if not website:
        return jsonify({'error': 'Website not found'}), 404

    if 'base_url' in data:
        
        base_url = data['base_url']
        
        parsed = urlparse(base_url)

        if not all([parsed.scheme, parsed.netloc]):
            return jsonify({'error': 'The provided URL is invalid'}), 400
    


        website.base_url = data['base_url']
    if 'last_scanned' in data:
        website.last_scanned = data['last_scanned']

    db.session.commit()
    return jsonify(website.to_dict()), 200

@website_bp.route('/activate', methods=['POST'])
@login_required
@user_is_admin
def activate_website():
    data = request.get_json()
    
    website_id = data.get('id')
    website = db.session.get(Website, website_id)
    if not website:
        return jsonify({'error': 'Website not found'}), 404

    should_activate = data.get('activate', False)
    website.active = should_activate
    db.session.commit()
    return jsonify(website.to_dict()), 200

@website_bp.route('/', methods=['GET'])
def get_websites():
    """Get a list of websites.

    Returns:
        json: A list of websites
    """
    params = request.args
    limit = params.get('limit', default=100, type=int)
    page = params.get('page', default=1, type=int)
    search = params.get('search', default=None, type=str)
    
    
    latest_report_subq = (
        db.session.query(
            Report.site_id,
            func.max(Report.timestamp).label('max_timestamp')
        )
        .group_by(Report.site_id)
        .subquery()
    )

    # Join websites to sites, sites to their most recent report, and order by violations
    w_query = (
        db.session.query(Website)
        .join(Site, Site.website_id == Website.id)
        .join(Report, Report.site_id == Site.id)
        .join(
            latest_report_subq,
            (latest_report_subq.c.site_id == Report.site_id) &
            (latest_report_subq.c.max_timestamp == Report.timestamp)
        )
        .order_by(func.json_extract(Report.report_counts, '$.violations.total').desc())
        .distinct()
    )
    if search:
        w_query = w_query.filter(Website.base_url.like(f"%{search}%"))
    w = w_query.paginate(page=page, per_page=limit)

    return jsonify({
        'count': w.total,
        'items': [website.to_dict() for website in w.items]
    }), 200

@website_bp.route('/<int:website_id>/sites', methods=['GET'])
def get_website_sites(website_id):
    params = request.args
    limit = params.get('limit', default=10, type=int)
    page = params.get('page', default=1, type=int)

    website = db.session.get(Website, website_id)
    if not website:
        return jsonify({'error': 'Website not found'}), 404

    latest_report_subq = (
        db.session.query(
            Report.site_id,
            func.max(Report.timestamp).label('max_timestamp')
        )
        .group_by(Report.site_id)
        .subquery()
    )

    # Join sites to their most recent report and order by violations
    sites_query = (
        db.session.query(Site)
        .join(Report, (Report.site_id == Site.id))
        .join(
            latest_report_subq,
            (latest_report_subq.c.site_id == Report.site_id) &
            (latest_report_subq.c.max_timestamp == Report.timestamp)
        )
        .filter(Site.website_id == website_id)
        .order_by(func.json_extract(Report.report_counts, '$.violations.total').desc())
    )

    sites = sites_query.paginate(page=page, per_page=limit)


    return jsonify({
        'count': sites.total,
        'items': [site.to_dict() for site in sites.items]
    }), 200

@website_bp.route('/<int:website_id>', methods=['GET'])
def get_overall_website(website_id):
    website = db.session.get(Website, website_id)
    if not website:
        return jsonify({'error': 'Website not found'}), 404

    return jsonify(website.to_dict()), 200

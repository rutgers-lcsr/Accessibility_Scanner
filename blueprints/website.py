import re
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, current_user
from authentication.login import admin_required
from mail.emails import NewWebsiteEmail
from models.report import AxeReportCounts, Report
from models.website import Domains, Site, Website 
from models import db

from scanner.accessibility.ace import AxeReportKeys
from sqlalchemy import Integer, cast, func

from utils.urls import get_netloc, is_valid_url
website_bp = Blueprint('website', __name__,  url_prefix="/websites")


@website_bp.route('/', methods=['POST'])
def create_website():
    data = request.get_json()
    base_url = data.get('base_url')
    email = data.get('email', None)
    if not base_url:
        return jsonify({'error': 'Base URL is required'}), 400
    
    # Check if valid URL
    if not is_valid_url(base_url):
        return jsonify({'error': 'The provided URL is invalid'}), 400

    website_netloc = get_netloc(base_url)
    all_domains = db.session.query(Domains).filter(Domains.active == True).all()
    best_match = None
    max_len = 0
    for domain in all_domains:
        if website_netloc.endswith(domain.domain) and len(domain.domain) > max_len:
            best_match = domain
            max_len = len(domain.domain)
    existing_domain = best_match

    if not existing_domain:
        return jsonify({'error': 'Domain is not found or is inactive'}), 400

    if not existing_domain.active:
        return jsonify({'error': 'The domain of the website your requested is not active, please contact the admins if you believe this is a problem'}), 400
    

    # check if website already exists
    existing_website = db.session.query(Website).filter_by(url=base_url).first()
    if existing_website:
        return jsonify({'error': 'Website already exists'}), 400

    new_website = Website(url=base_url, email=email)
    new_website.domain = existing_domain
    
    # send email to user and admin, user confirming and admin to activate


    db.session.add(new_website)
    db.session.commit()
    
    if email:
        NewWebsiteEmail(new_website).send()

    
    return jsonify(new_website.to_dict()), 201  

@website_bp.route('/<int:website_id>', methods=['PATCH'])
@admin_required
def update_website(website_id):
    data = request.get_json()
    website = db.session.get(Website, website_id)
    if not website:
        return jsonify({'error': 'Website not found'}), 404

    if 'base_url' in data:
        
        base_url = data['base_url']
        if not is_valid_url(base_url):
            return jsonify({'error': 'The provided URL is invalid'}), 400

        website.base_url = data['base_url']

    if 'last_scanned' in data:
        website.last_scanned = data['last_scanned']
    
    if 'active' in data:
        
        domain = db.session.get(Domains, website.domain_id)
        
        # scanner can add websites without a domain. this is because if a manual scan was made its not obvious what the parent domain might be.
        # some websites will be www.example.com, but some might be org.example.com, and its not always clear what the parent domain is.
        # if the domain is not found, we just use the website itself
        if domain and not domain.active and data['active']:
            return jsonify({'error': 'Cannot activate website because its domain is inactive'}), 400

        website.active = data['active'] and True
    if 'rate_limit' in data:
        website.rate_limit = data['rate_limit']
    if 'hard_limit' in data:
        website.hard_limit = data['hard_limit']
        
    if 'email' in data:
        email = str(data['email'])

        regex = r"[^@]+@[^@]+\.[^@]+"
        if not re.match(regex, email):
            return jsonify({'error': 'Invalid email format'}), 400

        # Email user that they have been added
        website.email = data['email']
    if 'should_email' in data:
        
        
        website.should_email = data['should_email'] and True
            
    db.session.add(website)
    db.session.commit()
    return jsonify(website.to_dict()), 200

@website_bp.route('/activate', methods=['POST'])
@jwt_required()
@admin_required
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

    # Query all websites, left join to sites and reports (so websites with no sites/reports are included)
    w_query = (
        db.session.query(Website)
        .outerjoin(Site, Site.website_id == Website.id)
        .outerjoin(Report, Report.site_id == Site.id)
        .outerjoin(
            latest_report_subq,
            (latest_report_subq.c.site_id == Report.site_id) &
            (latest_report_subq.c.max_timestamp == Report.timestamp)
        )
        .order_by(func.json_extract(Report.report_counts, '$.violations.total').desc().nullslast())
        .distinct()
    )
    if search:
        w_query = w_query.filter(Website.base_url.icontains(f"%{search}%"))
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

@website_bp.route('/<int:website_id>', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_website(website_id):
    website = db.session.get(Website, website_id)
    if not website:
        return jsonify({'error': 'Website not found'}), 404


    # Add Deleteing website email

    db.session.delete(website)
    db.session.commit()
    return jsonify({'message': 'Website deleted successfully'}), 200
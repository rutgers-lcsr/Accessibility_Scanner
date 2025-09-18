import asyncio
import re
from flask import Blueprint, jsonify, request, Response
from flask_jwt_extended import jwt_required, current_user
from authentication.login import  admin_required
from blueprints.scan import conduct_scan_website, loop
from mail.emails import AdminNewWebsiteEmail, NewWebsiteEmail, ScanFinishedEmail
from models.report import AxeReportCounts, Report
from models.user import User
from models.website import Domain, Site, Site_Website_Assoc, Website 
from models import db
from scanner.accessibility.ace import AxeReportKeys
from sqlalchemy import case, desc, func

from scanner.utils.service import check_url
from utils.urls import get_netloc, is_valid_url
website_bp = Blueprint('website', __name__,  url_prefix="/websites")


@website_bp.route('/', methods=['POST'])
@jwt_required()
def create_website():
    """
    Create a new website.
    ---
    tags:
        - Websites
    parameters:
        - in: body
            name: body
            required: true
            schema:
                type: object
                properties:
                    base_url:
                        type: string
                        example: "https://example.com"
                    should_email:
                        type: boolean
                        example: true
    responses:
        200:
            description: Website created successfully
            schema:
                type: object
                properties:
                    id:
                        type: integer
                    base_url:
                        type: string
        400:
            description: Invalid input
            schema:
                type: object
                properties:
                    error:
                        type: string
    """
    data = request.get_json()
    base_url = data.get('base_url')
    should_email = data.get('should_email', False)
    if not base_url:
        return jsonify({'error': 'Base URL is required'}), 400
    
    # Check if valid URL
    if not is_valid_url(base_url):
        return jsonify({'error': 'The provided URL is invalid'}), 400
        
    # check if user exists
    if not current_user:
        return jsonify({'error': 'User is not authenticated'}), 401
    try:
        is_accessible = check_url(base_url)
        if not is_accessible:
            return jsonify({'error': 'The provided URL is not accessible'}), 400

        new_website = Website(url=base_url, user_id=current_user.id)

        db.session.add(new_website)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

    try:
        if should_email and 'email' in data:
            NewWebsiteEmail(new_website).send()

        AdminNewWebsiteEmail(new_website).send()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

    asyncio.run_coroutine_threadsafe(conduct_scan_website(new_website.url), loop)

    return jsonify(new_website.to_dict()), 201
@website_bp.route('/email/<int:website_id>/', methods=['POST'])
@admin_required
def email_website_report(website_id):
    """
    Send a website report via email.
    ---
    tags:
        - Websites
    parameters:
        - in: path
            name: website_id
            required: true
            type: integer
        - in: body
            name: email
            required: false
            schema:
                type: object
                properties:
                    email:
                        type: string
    responses:
        200:
            description: Email sent successfully
            schema:
                type: object
                properties:
                    message:
                        type: string
        404:
            description: Website not found
            schema:
                type: object
                properties:
                    error:
                        type: string
        500:
            description: Error sending email
            schema:
                type: object
                properties:
                    error:
                        type: string
    """
    website = db.session.get(Website, website_id)
    data = request.get_json()
    email = data.get('email', None) if data else None
    if not website:
        return jsonify({'error': 'Website not found'}), 404
    try:
        ScanFinishedEmail(website).send(email=email, force=True)
        return jsonify({'message': 'Email sent successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@website_bp.route('/<int:website_id>/', methods=['PATCH'])
@admin_required
def update_website(website_id):
    """
    Update an existing website.
    ---
    tags:
        - Websites
    parameters:
        - in: path
            name: website_id
            required: true
            type: integer
        - in: body
            name: body
            required: true
            schema:
                type: object
                properties:
                    base_url:
                        type: string
                    last_scanned:
                        type: string
                    active:
                        type: boolean
                    rate_limit:
                        type: integer
                    hard_limit:
                        type: integer
                    email:
                        type: string
                    should_email:
                        type: boolean
                    public:
                        type: boolean
    responses:
        200:
            description: Website updated successfully
            schema:
                type: object
        400:
            description: Invalid input
            schema:
                type: object
                properties:
                    error:
                        type: string
        404:
            description: Website not found
            schema:
                type: object
                properties:
                    error:
                        type: string
    """
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
        domain = db.session.get(Domain, website.domain_id)
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
        user = db.session.query(User).filter_by(email=email).first()
        if not user:
            # since admins can only change email, assume they are the user
            user = User(email=email, username=email.split('@')[0])
            db.session.add(user)
        website.user = user

    if 'should_email' in data:
        website.should_email = data['should_email'] and True

    if 'public' in data:
        website.public = data['public'] and True

    if 'tags' in data:
        tags = data['tags']
        if isinstance(tags, list):
            # Clean tags and remove empty strings
            cleaned_tags = [tag.strip() for tag in tags if tag.strip()]
            website.tags = ",".join(cleaned_tags)
        elif isinstance(tags, str):
            # If a single string is provided, convert it to a list
            cleaned_tag = tags.strip().split(',')
            cleaned_tag = [tag.strip() for tag in cleaned_tag if tag.strip()]
            if cleaned_tag:
                website.tags = ",".join(cleaned_tag)
            else:
                website.tags = ""
        else:
            return jsonify({'error': 'Tags must be a list of strings or a single string'}), 400

    db.session.add(website)
    db.session.commit()
    return jsonify(website.to_dict()), 200

@website_bp.route('/activate', methods=['POST'])
@admin_required
def activate_website():
    """
    Activate or deactivate a website.
    ---
    tags:
        - Websites
    parameters:
        - in: body
            name: body
            required: true
            schema:
                type: object
                properties:
                    id:
                        type: integer
                    activate:
                        type: boolean
    responses:
        200:
            description: Website activation updated
            schema:
                type: object
        404:
            description: Website not found
            schema:
                type: object
                properties:
                    error:
                        type: string
    """
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
@jwt_required(optional=True)
def get_websites():
    """
    Get a list of websites.
    ---
    tags:
        - Websites
    parameters:
        - in: query
            name: limit
            type: integer
            required: false
            default: 100
        - in: query
            name: page
            type: integer
            required: false
            default: 1
        - in: query
            name: search
            type: string
            required: false
    responses:
        200:
            description: List of websites
            schema:
                type: object
                properties:
                    count:
                        type: integer
                    items:
                        type: array
                        items:
                            type: object
        403:
            description: Unauthorized
            schema:
                type: object
                properties:
                    error:
                        type: string
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
        db.session.query(Website).order_by(Website.url.asc())
        .outerjoin(Site_Website_Assoc, Site_Website_Assoc.c.website_id == Website.id)
        .outerjoin(Site, Site.id == Site_Website_Assoc.c.site_id)
        .outerjoin(Report, Report.site_id == Site.id)
        .outerjoin(
            latest_report_subq,
            (latest_report_subq.c.site_id == Report.site_id) &
            (latest_report_subq.c.max_timestamp == Report.timestamp)
        )
        .order_by(
            case((Report.report_counts == None, 1), else_=0),
            func.json_extract(Report.report_counts, '$.violations.total').desc()
        )
        .distinct()
    )
    if search:
        w_query = w_query.filter(Website.url.icontains(f"%{search}%"))

    if not current_user or not current_user.profile.is_admin:
        # make sure that non-admin users can only see public websites
        w_query = w_query.filter(Website.public == True)

    if current_user and not current_user.profile.is_admin:
        w_query = w_query.filter(Website.user_id == current_user.id)

    w = w_query.paginate(page=page, per_page=limit)


    return jsonify({
        'count': w.total,
        'items': [website.to_dict() for website in w.items]
    }), 200

@website_bp.route('/<int:website_id>/sites/', methods=['GET'])
@jwt_required(optional=True)
def get_website_sites(website_id):
    """
    Get a list of sites for a specific website.
    ---
    tags:
        - Websites
    parameters:
        - in: path
            name: website_id
            required: true
            type: integer
        - in: query
            name: limit
            type: integer
            required: false
            default: 10
        - in: query
            name: page
            type: integer
            required: false
            default: 1
    responses:
        200:
            description: List of sites for website
            schema:
                type: object
                properties:
                    count:
                        type: integer
                    items:
                        type: array
                        items:
                            type: object
        403:
            description: Unauthorized
            schema:
                type: object
                properties:
                    error:
                        type: string
        404:
            description: Website not found
            schema:
                type: object
                properties:
                    error:
                        type: string
    """
    params = request.args
    limit = params.get('limit', default=10, type=int)
    page = params.get('page', default=1, type=int)

    website = db.session.get(Website, website_id)
    if not website:
        return jsonify({'error': 'Website not found'}), 404

    if current_user:
        if not current_user.profile.is_admin and website.user_id != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403

    if not current_user or not current_user.profile.is_admin:
        # make sure that non-admin users can only see public websites
        if not website.public:
            return jsonify({'error': 'Unauthorized'}), 403

    latest_report_subq = (
        db.session.query(
            Report.site_id,
            func.max(Report.timestamp).label('max_timestamp')
        )
        .group_by(Report.site_id)
        .subquery()
    )
    site_subq = (
        db.session.query(Site.id).join(Site_Website_Assoc, Site_Website_Assoc.c.site_id == Site.id).filter(Site_Website_Assoc.c.website_id == website_id).subquery()
    )
    # Join sites to their most recent report and order by violations
    sites_query = (
        db.session.query(Site).order_by(Site.url.asc()).where(Site.id.in_(site_subq.select()))
        .join(Report, (Report.site_id == Site.id))
        .join(
            latest_report_subq,
            (latest_report_subq.c.site_id == Report.site_id) &
            (latest_report_subq.c.max_timestamp == Report.timestamp)
        )
        .order_by(func.json_extract(Report.report_counts, '$.violations.total').desc())
    )

    sites = sites_query.paginate(page=page, per_page=limit)

    return jsonify({
        'count': sites.total,
        'items': [site.to_dict() for site in sites.items]
    }), 200

@website_bp.route('/<int:website_id>/', methods=['GET'])
@jwt_required(optional=True)
def get_overall_website(website_id):
    """
    Get details for a specific website.
    ---
    tags:
        - Websites
    parameters:
        - in: path
            name: website_id
            required: true
            type: integer
    responses:
        200:
            description: Website details
            schema:
                type: object
        404:
            description: Website not found
            schema:
                type: object
                properties:
                    error:
                        type: string
    """
    website = db.session.get(Website, website_id)
    if not website:
        return jsonify({'error': 'Website not found'}), 404
    
    if current_user:
        if not current_user.profile.is_admin and website.user_id != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403

    return jsonify(website.to_dict()), 200

@website_bp.route('/<int:website_id>/axe/', methods=['GET'])
@jwt_required(optional=True)
def get_website_axe(website_id):
    """
    Get Axe configuration for a specific website.
    ---
    tags:
        - Websites
    parameters:
        - in: path
            name: website_id
            required: true
            type: integer
    responses:
        200:
            description: Axe configuration
            schema:
                type: object
        404:
            description: Website not found
            schema:
                type: object
                properties:
                    error:
                        type: string
    """
    website = db.session.get(Website, website_id)
    if not website:
        return jsonify({'error': 'Website not found'}), 404

    if current_user:
        if not current_user.profile.is_admin and website.user_id != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403

    response = Response(website.get_ace_config(), mimetype='application/json')
    response.headers['Content-Disposition'] = f'attachment; filename=website_{website_id}_ace_config.json'
    return response


@website_bp.route('/<int:website_id>/', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_website(website_id):
    """
    Delete a website.
    ---
    tags:
        - Websites
    parameters:
        - in: path
            name: website_id
            required: true
            type: integer
    responses:
        200:
            description: Website deleted successfully
            schema:
                type: object
                properties:
                    message:
                        type: string
        404:
            description: Website not found
            schema:
                type: object
                properties:
                    error:
                        type: string
    """
    website = db.session.get(Website, website_id)
    if not website:
        return jsonify({'error': 'Website not found'}), 404

    # Add Deleteing website email
    website.delete()
    return jsonify({'message': 'Website deleted successfully'}), 200
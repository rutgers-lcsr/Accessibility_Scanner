import json
from flask import Blueprint, current_app, jsonify, request, Response
from flask_jwt_extended import jwt_required, current_user
from authentication.login import  admin_required
from mail.emails import AdminNewWebsiteEmail, NewWebsiteEmail, ScanFinishedEmail
from models.report import  Report
from models.settings import Settings
from models.user import Profile, User
from models.website import Domain, Site, Site_Website_Assoc, Website 
from models import db
from sqlalchemy import case, func
from flask_sqlalchemy import pagination

from scanner.utils.service import check_url
from services.history import daily_history, effective_counts
from models.finding import FINDING_STATUSES
from services.findings import bulk_set_status, list_findings
from utils.limiter import limiter
from utils.urls import get_netloc, is_valid_url
website_bp = Blueprint('website', __name__,  url_prefix="/websites")


def _get_or_create_user(username: str):
    """The user called ``username``, created with the default email domain when missing.

    Returns ``(user, error)``; the new user is flushed, not committed, so a request that
    fails later leaves no user behind.
    """
    user = db.session.query(User).filter_by(username=username).first()
    if user:
        return user, None
    domain = Settings.get('default_email_domain', '')
    if not domain:
        return None, f'No email domain set to create user {username}, Please ask an admin to set a default'
    user = User(username=username, email=f"{username}@{domain}")
    user.profile = Profile(user=user, is_admin=False)
    db.session.add(user)
    db.session.flush()
    return user, None


def _csv_list(value) -> list:
    """Non-empty, stripped strings from a list or a comma-separated string."""
    if isinstance(value, str):
        value = value.split(',')
    if not isinstance(value, list):
        raise ValueError('Categories must be a list of strings or a comma-separated string')
    return [str(item).strip() for item in value if str(item).strip()]


@website_bp.route('/', methods=['POST'])
@limiter.limit("5/minute")
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
                    admin:
                        type: string
                        description: Site admins only. Username of the website's admin (created if unknown); defaults to the caller.
                    categories:
                        type: array
                        items:
                            type: string
                        description: Site admins only.
                    create_domain:
                        type: boolean
                        description: Site admins only. When the host is not under an allowed domain, allow-list the host and continue.
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

    is_admin = bool(current_user.profile and current_user.profile.is_admin)

    # Allow-list first: only hosts under an admin-added parent domain are ever probed,
    # so this endpoint cannot be used to test reachability of arbitrary hosts.
    if not Website.find_parent_domain(base_url):
        host = get_netloc(base_url).lower()
        if not (is_admin and data.get('create_domain')):
            # code/domain let the UI offer a site admin to allow-list the host and retry.
            return jsonify({
                'error': f'No active parent domain found for {host}, an administrator must add it first',
                'code': 'no_parent_domain',
                'domain': host,
            }), 400
        # Allow-list the host together with the website. Nothing is committed until the
        # website is, so a failed probe leaves no domain behind.
        domain = db.session.query(Domain).filter_by(domain=host).first()
        if domain is None:
            domain = Domain(domain=host)
        domain.active = True
        db.session.add(domain)

    admin_user = current_user
    if is_admin and data.get('admin'):
        admin_user, error = _get_or_create_user(str(data['admin']).strip())
        if error:
            db.session.rollback()
            return jsonify({'error': error}), 400

    try:
        is_accessible = check_url(base_url)
        if not is_accessible:
            db.session.rollback()
            return jsonify({'error': 'The provided URL is not accessible'}), 400

        new_website = Website(url=base_url, user_id=admin_user.id)
        if is_admin and 'categories' in data:
            new_website.categories = ",".join(_csv_list(data['categories']))

        db.session.add(new_website)
        db.session.commit()
    except ValueError as e:
        # Website() explains what is wrong (duplicate, no parent domain, ...)
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Error creating website %s", base_url)
        return jsonify({'error': 'Could not create the website'}), 500

    # The website is committed; a mail problem must not fail (or roll back) the request.
    try:
        if should_email:
            NewWebsiteEmail(new_website).send()

        AdminNewWebsiteEmail(new_website).send()
    except Exception:
        current_app.logger.exception("Error sending new-website mail for %s", base_url)

    if Settings.get('default_should_auto_scan', 'true').lower() == 'true':
        from scanner.tasks import scan_website
        scan_website.delay(new_website.url)

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

@website_bp.route('/<int:website_id>/notifications/', methods=['GET', 'PUT'])
@jwt_required()
def website_notifications(website_id):
    """
    Whether the caller receives this website's notification emails.
    ---
    tags:
        - Websites
    parameters:
        - in: path
          name: website_id
          type: integer
          required: true
        - in: body
          name: body
          required: false
          schema:
              type: object
              properties:
                  subscribed:
                      type: boolean
    responses:
        200:
            description: subscribed (this user's switch) and website_wide (the admin switch).
        400:
            description: subscribed missing or not a boolean.
        403:
            description: The caller may not view this website.
        404:
            description: Website not found.
    """
    website = db.session.get(Website, website_id)
    if not website:
        return jsonify({'error': 'Website not found'}), 404
    if not website.can_view(current_user):
        return jsonify({'error': 'Unauthorized'}), 403

    if request.method == 'PUT':
        data = request.get_json(silent=True) or {}
        if not isinstance(data.get('subscribed'), bool):
            return jsonify({'error': 'subscribed must be true or false'}), 400
        website.set_subscribed(current_user, data['subscribed'])

    return jsonify({
        'subscribed': website.is_subscribed(current_user),
        'website_wide': bool(website.should_email),
    }), 200


FINDING_LISTING_STATUSES = ('current', 'open', 'suppressed', 'fixed', 'all')


@website_bp.route('/<int:website_id>/findings/', methods=['GET'])
@jwt_required(optional=True)
def get_website_findings(website_id):
    """
    The website's findings grouped by rule and page.
    ---
    tags:
        - Findings
    parameters:
        - in: path
          name: website_id
          type: integer
          required: true
        - in: query
          name: status
          type: string
          enum: [current, open, suppressed, fixed, all]
          default: current
          description: current = present in each page's latest report.
        - in: query
          name: rule
          type: string
          description: Only this axe rule id.
    responses:
        200:
            description: count and rules, each with per-status counts and pages.
        403:
            description: The caller may not view this website.
        404:
            description: Website not found.
    """
    website = db.session.get(Website, website_id)
    if not website:
        return jsonify({'error': 'Website not found'}), 404
    if not current_user and not website.public:
        return jsonify({'error': 'Unauthorized'}), 403
    if current_user and not website.can_view(current_user):
        return jsonify({'error': 'Unauthorized'}), 403

    status = request.args.get('status', 'current')
    if status not in FINDING_LISTING_STATUSES:
        return jsonify({'error': f"status must be one of {', '.join(FINDING_LISTING_STATUSES)}"}), 400
    site_ids = [row.id for row in website.sites.with_entities(Site.id).all()]
    return jsonify(list_findings(site_ids, status, request.args.get('rule'))), 200


@website_bp.route('/<int:website_id>/findings/bulk/', methods=['POST'])
@jwt_required()
def bulk_update_website_findings(website_id):
    """
    Apply one verdict to every current finding of a rule on this website (or one page).
    ---
    tags:
        - Findings
    parameters:
        - in: path
          name: website_id
          type: integer
          required: true
        - in: body
          name: body
          required: true
          schema:
              type: object
              properties:
                  rule_id:
                      type: string
                  status:
                      type: string
                      enum: [open, fixed, false_positive, accepted]
                  note:
                      type: string
                  site_id:
                      type: integer
                      description: Limit to one page of the website.
    responses:
        200:
            description: updated = number of findings changed.
        400:
            description: Missing rule_id, unknown status, or a page not on this website.
        403:
            description: The caller may not edit this website.
        404:
            description: Website not found.
    """
    website = db.session.get(Website, website_id)
    if not website:
        return jsonify({'error': 'Website not found'}), 404
    if not website.can_edit(current_user):
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json(silent=True) or {}
    rule_id = data.get('rule_id')
    if not isinstance(rule_id, str) or not rule_id.strip():
        return jsonify({'error': 'rule_id is required'}), 400
    status = data.get('status')
    if status not in FINDING_STATUSES:
        return jsonify({'error': f"status must be one of {', '.join(FINDING_STATUSES)}"}), 400
    note = data.get('note')
    if note is not None and not isinstance(note, str):
        return jsonify({'error': 'note must be text'}), 400

    site_ids = [row.id for row in website.sites.with_entities(Site.id).all()]
    if data.get('site_id') is not None:
        if data['site_id'] not in site_ids:
            return jsonify({'error': 'That page is not part of this website'}), 400
        site_ids = [data['site_id']]

    updated = bulk_set_status(site_ids, rule_id.strip(), status, note, current_user.id)
    db.session.commit()
    return jsonify({'updated': updated}), 200


@website_bp.route('/<int:website_id>/', methods=['PATCH'])
@jwt_required()
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
                    admin:
                        type: integer
                    users:
                        type: array
                        items:
                            type: string
                    tags:
                        type: array
                        items:
                            type: string
                    extra_start_urls:
                        type: array
                        items:
                            type: string
                        description: Pages a full scan starts from besides the website URL (must be on the website's host).
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

    if not current_user:
        return jsonify({'error': 'User is not authenticated'}), 401
    
    if not website.can_edit(current_user):
        return jsonify({'error': 'Unauthorized'}), 403

    
        
    if 'users' in data:
        users = data['users']
        if isinstance(users, list):
            # First remove all existing users
            current_users = website.users[:]
            for user in current_users:
                website.remove_user(user, commit=False)
            # Now add the new users
            for username in users:
                user = db.session.query(User).filter_by(username=username).first()
                if user:
                    website.add_user(user, commit=False)
                else:
                    # add the user if they dont exist
                    domain = Settings.get('default_email_domain', '')
                    email = f"{username}@{domain}" if domain else None
                    if not email:
                        return jsonify({'error': f'No email domain set to create user {username}, Please ask an admin to set a default'}), 400
                    new_user = User(username=username, email=email)
                    new_user.profile = Profile(user=new_user, is_admin=False)
                    db.session.add(new_user)
                    db.session.commit()  # Commit to get the user ID
                    new_user =  db.session.query(User).filter_by(username=username).first()
                    website.add_user(new_user, commit=False)
        else:
            return jsonify({'error': 'Users must be a list of usernames'}), 400



    if 'extra_start_urls' in data:
        urls = data['extra_start_urls']
        if isinstance(urls, str):
            urls = urls.splitlines()
        if not isinstance(urls, list):
            return jsonify({'error': 'extra_start_urls must be a list of URLs'}), 400
        try:
            website.set_extra_start_urls(urls)
        except ValueError as e:
            return jsonify({'error': str(e)}), 400

    # Admin only fields
    if current_user.profile.is_admin:
        if 'public' in data:
            website.public = data['public'] and True
        if 'active' in data:
            website.active = data['active'] and True
        if 'rate_limit' in data:
            website.rate_limit = data['rate_limit'] 
        if 'should_email' in data:
            website.should_email = data['should_email'] and True
        if 'active' in data:
            domain = db.session.get(Domain, website.domain_id)
            # scanner can add websites without a domain. this is because if a manual scan was made its not obvious what the parent domain might be.
            # some websites will be www.example.com, but some might be org.example.com, and its not always clear what the parent domain is.
            # if the domain is not found, we just use the website itself
            if domain and not domain.active and data['active']:
                return jsonify({'error': 'Cannot activate website because its domain is inactive'}), 400
            website.active = data['active'] and True
        
        if 'admin' in data:
            admin_username = data['admin']
            admin_user = db.session.query(User).filter_by(username=admin_username).first()
            if not admin_user:
                domain = Settings.get('default_email_domain', '')
                email = f"{admin_username}@{domain}" if domain else None
                if not email:
                    return jsonify({'error': f'No email domain set to create user {admin_username}, Please ask an admin to set a default'}), 400
                new_user = User(username=admin_username, email=email)
                new_user.profile = Profile(user=new_user, is_admin=False)
                db.session.add(new_user)
                db.session.commit()  # Commit to get the user ID
                admin_user =  db.session.query(User).filter_by(username=admin_username).first()
                if not admin_user:
                    return jsonify({'error': f'Could not create user {admin_username}'}), 500
            if website.admin_id == admin_user.id:
                return jsonify({'error': 'The specified user is already the admin of this website'}), 400
            website.admin = admin_user
            # if the admin is being changed, make sure to email them
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

        if 'categories' in data:
            categories = data['categories']
            if isinstance(categories, list):
                # Clean categories and remove empty strings
                cleaned_categories = [cat.strip() for cat in categories if cat.strip()]
                website.categories = ",".join(cleaned_categories)
            elif isinstance(categories, str):
                # If a single string is provided, convert it to a list
                cleaned_cat = categories.strip().split(',')
                cleaned_cat = [cat.strip() for cat in cleaned_cat if cat.strip()]
                if cleaned_cat:
                    website.categories = ",".join(cleaned_cat)
                else:
                    website.categories = ""
            else:
                return jsonify({'error': 'Categories must be a list of strings or a single string'}), 400
        
        if 'description' in data:
            description = data['description']
            if isinstance(description, str):
                website.description = description.strip()
            else:
                return jsonify({'error': 'Description must be a string'}), 400

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
        - in: query
            name: category
            type: string
            required: false
        - in: query
            name: orderBy
            type: string
            required: false
            default: url
            enum: [url, last_scanned, violations]
        - in: query
            name: format
            type: string
            required: false
            enum: [csv]
        - in: query
            name: keys
            type: string
            required: false
            description: Comma separated list of keys to include in CSV export. If not provided, all keys will be included.
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
    categories = params.get('category', default=None, type=str)
    order_by = params.get('orderBy', default='url', type=str)
    
    # params for csv export
    format = params.get('format', default='', type=str)
    keys = params.get('keys', default='', type=str)
    keys = [k.strip() for k in keys.split(",") if k.strip()]
    # add id to keys
    if 'id' not in keys and len(keys) > 0:
        keys = ['id'] + keys

    if categories:
        categories = [c.strip() for c in categories.split(",") if c.strip()]
    # Query all websites, left join to sites and reports (so websites with no sites/reports are included)
    w_query = (
        db.session.query(Website)
    )
    
    match order_by:
        case 'last_scanned':
            w_query = w_query.order_by(Website.last_scanned.desc())
        case 'violations':
            subq = Website.get_report_counts()
            w_query = w_query.outerjoin(subq, Website.id == subq.c.website_id).order_by(func.coalesce(subq.c.violations_total, 0).desc())
        case 'url':
            w_query = w_query.order_by(Website.url.asc())
        case _:
            w_query = w_query.order_by(Website.url.asc())

    if categories:
        w_query = w_query.filter(
            case(
                *( (Website.categories.ilike(f"%{cat}%"), True) for cat in categories ),
                else_=False
            )
        )
    
    if search:
        w_query = w_query.filter(Website.url.icontains(f"%{search}%"))

    w_query = w_query.filter(Website.visible_to(current_user))



    if format == 'csv':
        from sqlalchemy.orm import joinedload

        w: pagination.Pagination[Website] = w_query.options(joinedload(Website.admin),joinedload(Website.users) ).paginate(page=page, per_page=limit)

        items: list[dict] = []
        for website in w.items:
            items.append(website.to_dict())
            
        if not items or len(items) == 0:
            return jsonify({'error': 'No websites found to export'}), 400

        def generate():
            # Generate CSV header
            if keys:
                yield ",".join(keys) + "\n"
            else:
                
                columns = items[0].keys()

                keys_to_remove = ['created_at', 'updated_at', 'description', 'report', 'should_email']
                # remove report key because its too complex for a csv

                columns = [c for c in columns if c not in keys_to_remove]
                
                yield ','.join(columns) + "\n"
            for website in items:

                if keys:
                    website = {k: website[k] for k in keys if k in website}
                    yield ",".join(str(website[k]) if k in website and website[k] is not None else "" for k in keys) + "\n"
                else:

                    def serialize_value(val):
                        if isinstance(val, (list, dict)):
                            # Escape double quotes by doubling them for CSV
                            json_str = json.dumps(val, ensure_ascii=False).replace('"', '""')
                            return f'"{json_str}"'
                        return str(val) if val is not None else ""
                    values = [serialize_value(website[k]) if k in website else "" for k in columns]

                    yield ",".join(values) + "\n"

        return Response(generate(), mimetype='text/csv', headers={"Content-Disposition": "attachment;filename=websites.csv"})


    w: pagination.Pagination[Website] = w_query.paginate(page=page, per_page=limit)
    if not w.items and page != 1 and w.total > 0:
        return jsonify({'error': 'Page number out of range'}), 400

    if not w:
        return jsonify({'count': 0, 'items': []}), 200

   

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
        if not website.can_view(current_user):
            return jsonify({'error': 'Unauthorized'}), 403

    if not current_user:
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
    # Join sites to their most recent report and order by violations. Outer joins keep
    # pages that have no report yet (every scan of them failed) in the listing so their
    # failure is visible; they sort last.
    sites_query = (
        db.session.query(Site).where(Site.id.in_(site_subq.select()))
        .outerjoin(latest_report_subq, latest_report_subq.c.site_id == Site.id)
        .outerjoin(
            Report,
            (Report.site_id == Site.id) &
            (Report.timestamp == latest_report_subq.c.max_timestamp)
        )
        .order_by((
            func.json_extract(Report.report_counts, '$.violations.total')
            - func.coalesce(func.json_extract(Report.suppressed_counts, '$.total'), 0)
        ).desc())
    )

    sites = sites_query.paginate(page=page, per_page=limit)

    return jsonify({
        'count': sites.total,
        'items': [site.to_dict() for site in sites.items]
    }), 200

@website_bp.route('/<int:website_id>/history/', methods=['GET'])
@jwt_required(optional=True)
def get_website_history(website_id):
    """
    Get the aggregated accessibility history for a website over time.
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
            description: Daily aggregated report counts across all the website's URLs
            schema:
                type: object
                properties:
                    items:
                        type: array
                        items:
                            type: object
        404:
            description: Website not found
    """
    website = db.session.get(Website, website_id)
    if not website:
        return jsonify({'error': 'Website not found'}), 404

    if current_user:
        if not website.can_view(current_user):
            return jsonify({'error': 'Unauthorized'}), 403

    if not current_user:
        # make sure that non-admin users can only see public websites
        if not website.public:
            return jsonify({'error': 'Unauthorized'}), 403

    # Pull only (site_id, timestamp, report_counts) for every report of this
    # website's URLs, oldest -> newest. Avoid loading the heavy report/photo blobs.
    reports = (
        db.session.query(Report.site_id, Report.timestamp, Report.report_counts, Report.suppressed_counts)
        .join(Site_Website_Assoc, Site_Website_Assoc.c.site_id == Report.site_id)
        .filter(Site_Website_Assoc.c.website_id == website_id)
        .order_by(Report.timestamp.asc())
        .all()
    )
    items = daily_history([(site_id, ts, effective_counts(counts, suppressed)) for site_id, ts, counts, suppressed in reports])

    return jsonify({'count': len(items), 'items': items}), 200

@website_bp.route('/categories/', methods=['GET'])
@jwt_required(optional=True)
def get_website_categories():
    """
    Get a list of categories for websites.
    ---
    tags:
        - Websites
    responses:
        200:
            description: List of categories
            schema:
                type: array
                items:
                    type: string
    """
    if not current_user:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Get all categories for websites the user can view, split and flatten them in Python
    categories_sql = db.session.query(Website.categories).filter(Website.categories.isnot(None), Website.categories != '').filter(Website.visible_to(current_user)).all()

    categories = []
    for cat in categories_sql:
        if  cat[0]:
            categories.extend([c.strip() for c in cat[0].split(",") if c.strip()])
    # Remove duplicates and sort
    categories = list(set(categories))
    categories.sort()

    return jsonify(categories), 200

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
    
    if not current_user:
        if not website.public:
            return jsonify({'error': 'Unauthorized'}), 403
    if not website.can_view(current_user):
        return jsonify({'error': 'Unauthorized'}), 403

    return jsonify(website.to_dict(with_report=True)), 200

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

    # can_view handles anonymous callers (public websites only) and members.
    if not website.can_view(current_user):
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
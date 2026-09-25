from urllib.parse import urlparse

from flask import Blueprint, Response, g, jsonify, request
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from authentication.api_key import api_key_required
from blueprints.website import create_website_for, update_website_for
from models import db
from models.report import Report
from models.rules import Rule
from models.website import Domain, Site, Website
from services.rules import RuleInputError, active_website_tags, build_rule, serialize_rule
from services.scan import (
    queue_site_scan,
    queue_website_scan,
    resolve_task_target,
    serialize_task_state,
    site_scan_in_progress,
)
from utils.limiter import limiter
from utils.markdown import (
    report_to_agent_prompt,
    report_to_markdown,
    website_report_to_agent_prompt,
    website_report_to_markdown,
)

api_bp = Blueprint('api', __name__)


def _render(report: Report):
    """Render a report in the format given by the ?format= query param."""
    fmt = request.args.get('format', default='json', type=str).lower()

    if fmt == 'json':
        return jsonify(report.to_dict()), 200

    if fmt == 'markdown':
        return Response(report_to_markdown(report), mimetype='text/markdown')

    if fmt == 'agent':
        return Response(report_to_agent_prompt(report), mimetype='text/markdown')

    if fmt == 'pdf':
        pdf_data = report.generate_pdf()
        if not pdf_data:
            return jsonify({'error': 'Error generating PDF, Please try again later.'}), 500
        escaped_url = report.url.replace("/", "_").replace(":", "_")
        pdf_name = f"report_{escaped_url}.pdf"
        return Response(
            pdf_data,
            mimetype='application/pdf',
            headers={"Content-Disposition": f"attachment;filename={pdf_name}"},
        )

    return jsonify({'error': f"Unknown format '{fmt}'. Use json, markdown, agent, or pdf."}), 400


def _serve_report(report: Report | None):
    if not report:
        return jsonify({'error': 'Report not found'}), 404
    if not report.can_view(g.api_user):
        return jsonify({'error': 'Unauthorized'}), 403
    return _render(report)


def _render_website(website: Website):
    """Render a website's aggregated report (all pages combined)."""
    fmt = request.args.get('format', default='json', type=str).lower()

    if fmt == 'json':
        return jsonify({
            'website_id': website.id,
            'url': website.url,
            'report_counts': website.get_report_counts(),
            'report': website.get_report(),
        }), 200

    if fmt == 'markdown':
        return Response(website_report_to_markdown(website), mimetype='text/markdown')

    if fmt == 'agent':
        return Response(website_report_to_agent_prompt(website), mimetype='text/markdown')

    if fmt == 'pdf':
        return jsonify({
            'error': 'PDF is not available for the website-level aggregate. '
                     'Use a site or report endpoint for a PDF.'
        }), 400

    return jsonify({'error': f"Unknown format '{fmt}'. Use json, markdown, or agent."}), 400


def _render_report_list(website: Website, reports: list[Report]):
    """Render the latest report of each page under a website."""
    fmt = request.args.get('format', default='json', type=str).lower()

    if fmt == 'json':
        return jsonify({
            'website_id': website.id,
            'url': website.url,
            'reports': [r.to_dict() for r in reports],
        }), 200

    if fmt == 'markdown':
        body = "\n\n---\n\n".join(report_to_markdown(r) for r in reports)
        return Response(body, mimetype='text/markdown')

    if fmt == 'agent':
        # Only include pages that actually have violations to fix.
        with_violations = [r for r in reports if r.report.get('violations')]
        body = "\n\n---\n\n".join(report_to_agent_prompt(r) for r in with_violations)
        return Response(body, mimetype='text/markdown')

    if fmt == 'pdf':
        return jsonify({
            'error': 'PDF is not available for a multi-page latest report. '
                     'Use a single report or site endpoint for a PDF.'
        }), 400

    return jsonify({'error': f"Unknown format '{fmt}'. Use json, markdown, or agent."}), 400


def _normalize_host(raw: str) -> str | None:
    """Lower-cased hostname of ``raw``, which may be a bare host or a full URL.

    Returns None when no hostname can be read from it. utils.urls.get_netloc is not
    used because it only recognizes lower-case schemes.
    """
    raw = raw.strip().lower()
    if not raw.startswith(('http://', 'https://')):
        raw = 'https://' + raw
    try:
        host = urlparse(raw).hostname or ''
    except ValueError:  # unbalanced IPv6 bracket
        return None
    return host.strip('.') or None


def _host_suffixes(host: str) -> list[str]:
    """Every domain ``host`` is or sits under: a.b.edu -> [a.b.edu, b.edu, edu]."""
    labels = host.split('.')
    return ['.'.join(labels[i:]) for i in range(len(labels))]


def _search_params() -> tuple[int, int, str | None, str | None]:
    """page, limit, search and normalized host from the query string.

    Blank search/host are treated as absent. Raises ValueError with a message
    suitable for a 400 response when a value is unusable.
    """
    page = request.args.get('page', default=1, type=int)
    limit = request.args.get('limit', default=100, type=int)
    if page < 1 or limit < 1:
        raise ValueError('page and limit must be at least 1')
    search = request.args.get('search', default='', type=str).strip() or None
    host = request.args.get('host', default='', type=str).strip() or None
    if host is not None:
        host = _normalize_host(host)
        if host is None:
            raise ValueError('host is not a valid host or URL')
    return page, limit, search, host


@api_bp.route('/websites', methods=['GET'])
@api_key_required
def list_websites():
    """Search websites by URL substring or exact host.

    Lists the websites the key's owner can view: public ones, their own, and those
    they are a member of (everything for site admins). A count of 0 therefore means
    the website is absent or not visible to the key's owner. Use this to check
    whether a site is already in the scanner before adding it.
    ---
    tags:
      - Websites
    parameters:
      - name: search
        in: query
        type: string
        required: false
        description: Case-insensitive substring of the website URL.
      - name: host
        in: query
        type: string
        required: false
        description: >
          Bare hostname or full URL. Matches websites whose host is exactly this
          (case-insensitive, ASCII hostnames); example.edu does not match
          www.example.edu. Use search for a broader match. Combinable with search.
      - name: page
        in: query
        type: integer
        required: false
        default: 1
        description: Page number, starting at 1. A page past the end returns no items.
      - name: limit
        in: query
        type: integer
        required: false
        default: 100
        description: Results per page, capped at 100.
    responses:
      200:
        description: count (total matches) and items (the websites on this page).
      400:
        description: page or limit below 1, or host is not a valid host or URL.
      401:
        description: Missing, invalid, or revoked API key.
    """
    try:
        page, limit, search, host = _search_params()
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    query = db.session.query(Website).filter(Website.visible_to(g.api_user))
    if search:
        query = query.filter(Website.url.icontains(search, autoescape=True))
    if host:
        query = query.filter(Website.domain.has(func.lower(Domain.domain) == host))
    result = query.order_by(Website.url.asc()).paginate(
        page=page, per_page=limit, max_per_page=100, error_out=False
    )
    return jsonify({
        'count': result.total,
        'items': [website.to_dict() for website in result.items],
    }), 200


@api_bp.route('/websites', methods=['POST'])
@limiter.limit("5/minute")
@api_key_required
def create_website_endpoint():
    """Add a website to the scanner.

    Works like adding a website in the app: the host must be under an active
    allow-listed domain, the URL is probed for reachability, the key's owner becomes
    the website's admin, and a scan is queued when automatic scanning is enabled.
    Site admins may also allow-list the host, choose the admin and set categories.
    Check first with GET /api/v1/websites?host= and GET /api/v1/domains?host=.
    ---
    tags:
      - Websites
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - base_url
          properties:
            base_url:
              type: string
              example: "https://cs.example.edu"
              description: The website's root URL, scheme included.
            should_email:
              type: boolean
              default: false
              description: Also email the website's admin that it was added.
            admin:
              type: string
              description: >
                Site admins only. Username of the website's admin (created if unknown);
                defaults to the key's owner.
            categories:
              type: array
              items:
                type: string
              description: Site admins only.
            create_domain:
              type: boolean
              description: >
                Site admins only. When the host is not under an allowed domain,
                allow-list the host and continue.
    responses:
      201:
        description: The new website (same shape as the search results).
      400:
        description: >
          Invalid input. When the host is not allow-listed the body also carries
          code "no_parent_domain" and the host in "domain". A duplicate URL or an
          unreachable site is reported in "error".
      401:
        description: Missing, invalid, or revoked API key.
      429:
        description: More than 5 requests per minute.
    """
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'error': 'A JSON object body is required'}), 400
    return create_website_for(g.api_user, data)


@api_bp.route('/websites/<int:website_id>', methods=['PATCH'])
@api_key_required
def update_website_endpoint(website_id):
    """Update a website's settings.

    Only the fields present in the body change. The key's owner must be the
    website's admin or a site admin. Website admins may change users and
    extra_start_urls; every other field is applied only for site admins and is
    silently ignored otherwise.
    ---
    tags:
      - Websites
    consumes:
      - application/json
    parameters:
      - name: website_id
        in: path
        type: integer
        required: true
        description: Numeric website ID (from the search results).
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            users:
              type: array
              items:
                type: string
              description: Usernames who may view the website; replaces the current list. Unknown users are created.
            extra_start_urls:
              type: array
              items:
                type: string
              description: Pages a full scan starts from besides the website URL; must be on the website's host.
            description:
              type: string
              description: Site admins only.
            categories:
              type: array
              items:
                type: string
              description: Site admins only. A comma-separated string is also accepted.
            tags:
              type: array
              items:
                type: string
              description: Site admins only. axe tags used when scanning. A comma-separated string is also accepted.
            public:
              type: boolean
              description: Site admins only. Whether the reports are visible without logging in.
            active:
              type: boolean
              description: Site admins only. Cannot be set to true while the website's domain is inactive.
            rate_limit:
              type: integer
              description: Site admins only. Days between automatic scans.
            should_email:
              type: boolean
              description: Site admins only. Email the website's users when a scan finishes.
            admin:
              type: string
              description: Site admins only. Username of the new website admin (created if unknown).
    responses:
      200:
        description: The updated website.
      400:
        description: Invalid input, or a body that is not a JSON object.
      401:
        description: Missing, invalid, or revoked API key.
      403:
        description: The key's owner cannot edit this website.
      404:
        description: Website not found.
    """
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'error': 'A JSON object body is required'}), 400
    website = db.session.get(Website, website_id)
    if not website:
        return jsonify({'error': 'Website not found'}), 404
    if not website.can_edit(g.api_user):
        return jsonify({'error': 'Unauthorized'}), 403
    return update_website_for(g.api_user, website, data)


@api_bp.route('/domains', methods=['GET'])
@api_key_required
def list_domains():
    """Search the domain allow-list (site admins only).

    With host, returns every allow-list entry the host is or sits under, most
    specific first: sub.cs.example.edu returns cs.example.edu and example.edu when
    both exist. Inactive entries are included; check the active field. A website
    can only be added when at least one active entry covers its host.
    ---
    tags:
      - Domains
    parameters:
      - name: search
        in: query
        type: string
        required: false
        description: Case-insensitive substring of the domain name.
      - name: host
        in: query
        type: string
        required: false
        description: >
          Bare hostname or full URL. Returns the entries that are this host or one
          of its parent domains (case-insensitive, ASCII hostnames), longest first.
          Combinable with search.
      - name: page
        in: query
        type: integer
        required: false
        default: 1
        description: Page number, starting at 1. A page past the end returns no items.
      - name: limit
        in: query
        type: integer
        required: false
        default: 100
        description: Results per page, capped at 100.
    responses:
      200:
        description: count (total matches) and items (the domains on this page).
      400:
        description: page or limit below 1, or host is not a valid host or URL.
      401:
        description: Missing, invalid, or revoked API key.
      403:
        description: The key's owner is not a site admin.
    """
    if not (g.api_user.profile is not None and g.api_user.profile.is_admin):
        return jsonify({'error': 'Unauthorized'}), 403
    try:
        page, limit, search, host = _search_params()
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    query = db.session.query(Domain)
    if search:
        query = query.filter(Domain.domain.icontains(search, autoescape=True))
    if host:
        query = query.filter(func.lower(Domain.domain).in_(_host_suffixes(host))).order_by(
            func.length(Domain.domain).desc(), Domain.id.asc()
        )
    else:
        query = query.order_by(Domain.domain.asc())
    result = query.paginate(page=page, per_page=limit, max_per_page=100, error_out=False)
    return jsonify({
        'count': result.total,
        'items': [domain.to_dict() for domain in result.items],
    }), 200


@api_bp.route('/rules', methods=['GET'])
@api_key_required
def list_rules_endpoint():
    """List the custom axe rules (site admins only).

    Each rule is returned with its checks, in the shape POST /api/v1/rules accepts.
    ---
    tags:
      - Rules
    parameters:
      - name: search
        in: query
        type: string
        required: false
        description: Case-insensitive substring of the rule name.
      - name: page
        in: query
        type: integer
        required: false
        default: 1
        description: Page number, starting at 1. A page past the end returns no items.
      - name: limit
        in: query
        type: integer
        required: false
        default: 100
        description: Results per page, capped at 100.
    responses:
      200:
        description: count (total matches) and items (the rules on this page).
      400:
        description: page or limit below 1.
      401:
        description: Missing, invalid, or revoked API key.
      403:
        description: The key's owner is not a site admin.
    """
    if not (g.api_user.profile is not None and g.api_user.profile.is_admin):
        return jsonify({'error': 'Unauthorized'}), 403
    try:
        page, limit, search, _ = _search_params()
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    query = db.session.query(Rule)
    if search:
        query = query.filter(Rule.name.icontains(search, autoescape=True))
    result = query.order_by(Rule.name.asc()).paginate(
        page=page, per_page=limit, max_per_page=100, error_out=False
    )
    website_tags = active_website_tags()
    return jsonify({
        'count': result.total,
        'items': [serialize_rule(rule, website_tags) for rule in result.items],
    }), 200


@api_bp.route('/rules/<int:rule_id>', methods=['GET'])
@api_key_required
def get_rule_endpoint(rule_id):
    """Get a custom axe rule with its checks (site admins only).
    ---
    tags:
      - Rules
    parameters:
      - name: rule_id
        in: path
        type: integer
        required: true
        description: Numeric rule ID.
    responses:
      200:
        description: The rule, in the shape POST /api/v1/rules accepts.
      401:
        description: Missing, invalid, or revoked API key.
      403:
        description: The key's owner is not a site admin.
      404:
        description: Rule not found.
    """
    if not (g.api_user.profile is not None and g.api_user.profile.is_admin):
        return jsonify({'error': 'Unauthorized'}), 403
    rule = db.session.get(Rule, rule_id)
    if not rule:
        return jsonify({'error': 'Rule not found'}), 404
    return jsonify(serialize_rule(rule, active_website_tags())), 200


@api_bp.route('/rules', methods=['POST'])
@limiter.limit("30/minute")
@api_key_required
def create_rule_endpoint():
    """Create a custom axe rule together with its checks (site admins only).

    A rule selects elements with selector (narrowed by matches when given) and runs its
    checks on each of them. An element passes when at least one "any" check returns
    true, every "all" check returns true, and no "none" check returns true. A check that
    returns undefined marks the element for manual review (incomplete).

    A website's scans run the rule only when one of the rule's tags is among the
    website's scan tags. Every website scans with the default tags from Settings
    (e.g. wcag2a, wcag2aa) plus its own; websites_running in the response is the number
    of active websites whose scans will run the rule. Scans started after the rule is
    saved use it.

    Every problem in the body is reported in one response. Add ?dry_run=true to validate
    without saving. GET /api/v1/rules returns existing rules in the same shape; their
    id, created_at, updated_at and websites_running fields are ignored here.
    ---
    tags:
      - Rules
    consumes:
      - application/json
    definitions:
      RuleCheck:
        type: object
        required:
          - name
          - evaluate
          - pass_text
          - fail_text
        properties:
          name:
            type: string
            example: "alt-is-file-name"
            description: >
              Check ID, unique across all custom checks, at most 255 characters, and
              not an axe-core check ID such as has-alt.
          evaluate:
            type: string
            example: "(node) => ['.png', '.jpg', '.gif'].some((ext) => node.getAttribute('alt').trim().toLowerCase().endsWith(ext))"
            description: >
              JavaScript arrow function (node, options, virtualNode) => boolean, run in
              the scanned page for each selected element. node is the DOM Element and
              options is this check's options object; the first parameter must be named
              node. Return true or false, or undefined when the result needs manual
              review. Arrow functions have no this, so axe's this.data() and
              this.relatedNodes() are unavailable. Comments are removed when saved.
          options:
            type: object
            description: Passed to evaluate as its second argument.
          pass_text:
            type: string
            example: "Alt text is not a file name"
            description: >
              Report message when the check passes the element: evaluate returned
              true in any or all, false in none.
          fail_text:
            type: string
            example: "Alt text is a file name"
            description: >
              Report message when the check fails the element: evaluate returned
              false in any or all, true in none.
          incomplete_text:
            type: string
            description: Report message when evaluate returns undefined.
    parameters:
      - name: dry_run
        in: query
        type: boolean
        required: false
        default: false
        description: Validate the rule and report websites_running without saving it.
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - name
            - description
            - help
            - impact
            - tags
          properties:
            name:
              type: string
              example: "image-alt-not-file-name"
              description: >
                Rule ID shown in reports; unique, at most 255 characters, and not an
                axe-core rule ID such as image-alt.
            description:
              type: string
              example: "Ensures image alt text is not the image's file name"
              description: What the rule checks.
            help:
              type: string
              example: "Image alt text must describe the image, not name its file"
              description: Short summary of the problem, shown as the issue title in reports.
            help_url:
              type: string
              description: Page explaining the issue and how to fix it. Must resolve.
            impact:
              type: string
              enum: [minor, moderate, serious, critical]
            tags:
              type: array
              items:
                type: string
              example: ["wcag2a", "wcag111"]
              description: >
                At least one; no commas. Decides which websites run the rule (see
                above). Spaces become underscores.
            selector:
              type: string
              default: "*"
              example: "img[alt]"
              description: CSS selector of the elements to check. At most 255 characters.
            matches:
              type: string
              example: "(node) => node.getAttribute('alt').trim() !== ''"
              description: >
                Optional JavaScript arrow function (node, virtualNode) => boolean that
                further filters the selected elements; the first parameter must be
                named node.
            exclude_hidden:
              type: boolean
              default: true
              description: Skip elements hidden from all users.
            enabled:
              type: boolean
              default: true
              description: Disabled rules are saved but not run.
            any:
              type: array
              items:
                $ref: '#/definitions/RuleCheck'
              description: New checks of which at least one must return true.
            all:
              type: array
              items:
                $ref: '#/definitions/RuleCheck'
              description: New checks that must all return true.
            none:
              type: array
              items:
                $ref: '#/definitions/RuleCheck'
              description: New checks that must all return false.
    responses:
      200:
        description: dry_run only. The rule as it would be saved, with id null.
      201:
        description: The saved rule, in the shape GET /api/v1/rules/{rule_id} returns.
      400:
        description: >
          The rule is not valid. errors lists every problem as {field, message}, with
          field a path into the body such as "name" or "none[0].evaluate" ("rule" for
          problems with the rule as a whole).
      401:
        description: Missing, invalid, or revoked API key.
      403:
        description: The key's owner is not a site admin.
      409:
        description: A rule or check with the same name was saved at the same time.
      429:
        description: More than 30 requests per minute.
    """
    if not (g.api_user.profile is not None and g.api_user.profile.is_admin):
        return jsonify({'error': 'Unauthorized'}), 403
    try:
        rule = build_rule(request.get_json(silent=True))
    except RuleInputError as e:
        return jsonify({'error': 'The rule is not valid', 'errors': e.errors}), 400

    if request.args.get('dry_run', default='', type=str).lower() in ('1', 'true'):
        return jsonify(serialize_rule(rule, active_website_tags())), 200

    db.session.add(rule)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'A rule or check with this name already exists'}), 409
    return jsonify(serialize_rule(rule, active_website_tags())), 201


@api_bp.route('/reports/<int:report_id>', methods=['GET'])
@api_key_required
def get_report(report_id):
    """Get a report by ID.
    ---
    tags:
      - Reports
    produces:
      - application/json
      - text/markdown
      - application/pdf
    parameters:
      - name: report_id
        in: path
        type: integer
        required: true
        description: Numeric report ID.
      - name: format
        in: query
        type: string
        required: false
        enum: [json, markdown, agent, pdf]
        default: json
        description: >
          Output format. json = full machine-readable report;
          markdown = human-readable summary; agent = AI fix-prompt;
          pdf = downloadable PDF.
    responses:
      200:
        description: The report in the requested format.
      400:
        description: Unknown format.
      401:
        description: Missing, invalid, or revoked API key.
      403:
        description: The key's owner cannot view this report.
      404:
        description: Report not found.
    """
    return _serve_report(db.session.get(Report, report_id))


@api_bp.route('/reports/latest', methods=['GET'])
@api_key_required
def get_latest_report_by_url():
    """Get the most recent report for an exact page URL.
    ---
    tags:
      - Reports
    produces:
      - application/json
      - text/markdown
      - application/pdf
    parameters:
      - name: url
        in: query
        type: string
        required: true
        description: Exact page URL to look up.
      - name: format
        in: query
        type: string
        required: false
        enum: [json, markdown, agent, pdf]
        default: json
        description: Output format.
    responses:
      200:
        description: The latest report for the URL in the requested format.
      400:
        description: Missing url parameter or unknown format.
      401:
        description: Missing, invalid, or revoked API key.
      403:
        description: The key's owner cannot view this report.
      404:
        description: No report found for that URL.
    """
    url = request.args.get('url', type=str)
    if not url:
        return jsonify({'error': 'url query parameter is required'}), 400
    report = (
        db.session.query(Report)
        .filter(Report.url == url)
        .order_by(Report.timestamp.desc())
        .first()
    )
    return _serve_report(report)


@api_bp.route('/sites/<int:site_id>/reports/latest', methods=['GET'])
@api_key_required
def get_latest_report_by_site(site_id):
    """Get the most recent report for a site.
    ---
    tags:
      - Reports
    produces:
      - application/json
      - text/markdown
      - application/pdf
    parameters:
      - name: site_id
        in: path
        type: integer
        required: true
        description: Numeric site ID.
      - name: format
        in: query
        type: string
        required: false
        enum: [json, markdown, agent, pdf]
        default: json
        description: Output format.
    responses:
      200:
        description: The latest report for the site in the requested format.
      400:
        description: Unknown format.
      401:
        description: Missing, invalid, or revoked API key.
      403:
        description: The key's owner cannot view this report.
      404:
        description: Site not found, or it has no reports.
    """
    site = db.session.get(Site, site_id)
    if not site:
        return jsonify({'error': 'Site not found'}), 404
    return _serve_report(site.get_full_current_report())


@api_bp.route('/websites/<int:website_id>/report', methods=['GET'])
@api_key_required
def get_website_report(website_id):
    """Get a website's aggregated report (violations across all pages).
    ---
    tags:
      - Websites
    produces:
      - application/json
      - text/markdown
    parameters:
      - name: website_id
        in: path
        type: integer
        required: true
        description: Numeric website ID (the ID shown for a website in the app).
      - name: format
        in: query
        type: string
        required: false
        enum: [json, markdown, agent]
        default: json
        description: >
          Output format. Combines the current report of every page under the
          website. PDF is not supported here — use a site or report endpoint.
    responses:
      200:
        description: The aggregated website report in the requested format.
      400:
        description: Unknown format, or pdf requested (unsupported for the aggregate).
      401:
        description: Missing, invalid, or revoked API key.
      403:
        description: The key's owner cannot view this website.
      404:
        description: Website not found.
    """
    website = db.session.get(Website, website_id)
    if not website:
        return jsonify({'error': 'Website not found'}), 404
    if not website.can_view(g.api_user):
        return jsonify({'error': 'Unauthorized'}), 403
    return _render_website(website)


@api_bp.route('/websites/<int:website_id>/reports/latest', methods=['GET'])
@api_key_required
def get_latest_report_by_website(website_id):
    """Get the latest report for every page of a website (one per page).
    ---
    tags:
      - Websites
    produces:
      - application/json
      - text/markdown
    parameters:
      - name: website_id
        in: path
        type: integer
        required: true
        description: Numeric website ID.
      - name: format
        in: query
        type: string
        required: false
        enum: [json, markdown, agent]
        default: json
        description: >
          Output format. json returns a list of the latest report per page;
          markdown/agent concatenate one section per page. PDF is not supported
          here — use a single report or site endpoint.
    responses:
      200:
        description: The latest report of each page under the website.
      400:
        description: Unknown format, or pdf requested (unsupported).
      401:
        description: Missing, invalid, or revoked API key.
      403:
        description: The key's owner cannot view this website.
      404:
        description: Website not found, or it has no reports.
    """
    website = db.session.get(Website, website_id)
    if not website:
        return jsonify({'error': 'Website not found'}), 404
    if not website.can_view(g.api_user):
        return jsonify({'error': 'Unauthorized'}), 403

    reports = []
    for site in website.sites:
        report = site.get_full_current_report()
        if report:
            reports.append(report)
    if not reports:
        return jsonify({'error': 'Report not found'}), 404

    reports.sort(key=lambda r: r.url)
    return _render_report_list(website, reports)


@api_bp.route('/websites/<int:website_id>/scan', methods=['POST'])
@limiter.limit("5/minute")
@api_key_required
def scan_website_endpoint(website_id):
    """Queue a scan of every page of a website.

    Scanning runs in the background. Poll the returned status endpoint until the
    state is SUCCESS, then fetch the report from the report endpoint.
    ---
    tags:
      - Scans
    parameters:
      - name: website_id
        in: path
        type: integer
        required: true
        description: Numeric website ID.
    responses:
      202:
        description: Scan queued (or already in progress). Returns task_id and endpoints.
      401:
        description: Missing, invalid, or revoked API key.
      403:
        description: The key's owner cannot scan this website.
      404:
        description: Website not found.
    """
    website = db.session.get(Website, website_id)
    if not website:
        return jsonify({'error': 'Website not found'}), 404
    if not website.can_scan(g.api_user):
        return jsonify({'error': 'Unauthorized'}), 403

    task_id, queued = queue_website_scan(website)
    return jsonify({
        'message': 'Scan queued' if queued else 'Scan already in progress',
        'task_id': task_id,
        'status_endpoint': f'/api/v1/scans/{task_id}',
        'report_endpoint': f'/api/v1/websites/{website_id}/reports/latest',
    }), 202


@api_bp.route('/sites/<int:site_id>/scan', methods=['POST'])
@limiter.limit("5/minute")
@api_key_required
def scan_site_endpoint(site_id):
    """Queue a scan of a single page (site).
    ---
    tags:
      - Scans
    parameters:
      - name: site_id
        in: path
        type: integer
        required: true
        description: Numeric site (page) ID.
    responses:
      202:
        description: Scan queued. Returns task_id and endpoints.
      401:
        description: Missing, invalid, or revoked API key.
      403:
        description: The key's owner cannot scan this site.
      404:
        description: Site not found.
      409:
        description: A scan for this site is already in progress.
    """
    site = db.session.get(Site, site_id)
    if not site:
        return jsonify({'error': 'Site not found'}), 404
    if not site.can_scan(g.api_user):
        return jsonify({'error': 'Unauthorized'}), 403
    if site_scan_in_progress(site):
        return jsonify({'error': 'Scan already in progress'}), 409

    task_id = queue_site_scan(site)
    return jsonify({
        'message': 'Scan queued',
        'task_id': task_id,
        'status_endpoint': f'/api/v1/scans/{task_id}',
        'report_endpoint': f'/api/v1/sites/{site_id}/reports/latest',
    }), 202


@api_bp.route('/scans/<task_id>', methods=['GET'])
@api_key_required
def get_scan_status_endpoint(task_id):
    """Get the status of a queued scan.

    State is one of PENDING, PROGRESS, SUCCESS, or FAILURE. When SUCCESS, fetch
    the report from the relevant report endpoint. Only tasks for websites or sites
    the key's owner can view are returned.
    ---
    tags:
      - Scans
    parameters:
      - name: task_id
        in: path
        type: string
        required: true
        description: Task ID returned by a scan request.
    responses:
      200:
        description: Scan status.
      401:
        description: Missing, invalid, or revoked API key.
      404:
        description: No visible website or site has a scan with this task id.
    """
    target = resolve_task_target(task_id)
    if not target or not target.can_view(g.api_user):
        return jsonify({'error': 'Task not found'}), 404

    return jsonify(serialize_task_state(task_id)), 200

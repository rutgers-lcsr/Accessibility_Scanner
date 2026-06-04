from flask import Blueprint, Response, g, jsonify, request

from authentication.api_key import api_key_required
from models import db
from models.report import Report
from models.website import Site, Website
from scanner.tasks import scan_site as scan_site_task
from scanner.tasks import scan_website as scan_website_task
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


def _scan_in_progress(task_id: str | None) -> bool:
    if not task_id:
        return False
    return scan_website_task.AsyncResult(task_id).state in ('PENDING', 'PROGRESS')


@api_bp.route('/websites/<int:website_id>/scan', methods=['POST'])
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

    if _scan_in_progress(website.current_task_id):
        return jsonify({
            'message': 'Scan already in progress',
            'task_id': website.current_task_id,
            'status_endpoint': f'/api/v1/scans/{website.current_task_id}',
            'report_endpoint': f'/api/v1/websites/{website_id}/reports/latest',
        }), 202

    task = scan_website_task.delay(website.url)
    website.current_task_id = task.id
    db.session.commit()
    return jsonify({
        'message': 'Scan queued',
        'task_id': task.id,
        'status_endpoint': f'/api/v1/scans/{task.id}',
        'report_endpoint': f'/api/v1/websites/{website_id}/reports/latest',
    }), 202


@api_bp.route('/sites/<int:site_id>/scan', methods=['POST'])
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
    if site.scanning:
        return jsonify({'error': 'Scan already in progress'}), 409

    task = scan_site_task.delay(site.url)
    return jsonify({
        'message': 'Scan queued',
        'task_id': task.id,
        'status_endpoint': f'/api/v1/scans/{task.id}',
        'report_endpoint': f'/api/v1/sites/{site_id}/reports/latest',
    }), 202


@api_bp.route('/scans/<task_id>', methods=['GET'])
@api_key_required
def get_scan_status_endpoint(task_id):
    """Get the status of a queued scan.

    State is one of PENDING, PROGRESS, SUCCESS, or FAILURE. When SUCCESS, fetch
    the report from the relevant report endpoint.
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
    """
    from celery.result import AsyncResult

    from celery_app import celery

    task = AsyncResult(task_id, app=celery)
    state = task.state
    response = {'task_id': task_id, 'state': state}

    if state == 'PROGRESS':
        info = task.info or {}
        response['status'] = info.get('status', '')
        response['current'] = info.get('current', 0)
        response['total'] = info.get('total', 1)
    elif state == 'SUCCESS':
        response['result'] = task.result
    elif state == 'FAILURE':
        response['status'] = str(task.info)
    else:
        response['status'] = str(task.info) if task.info else ''

    return jsonify(response), 200

from flask import Blueprint, Response, g, jsonify, request

from authentication.api_key import api_key_required
from models import db
from models.report import Report
from models.website import Site
from utils.markdown import report_to_agent_prompt, report_to_markdown

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

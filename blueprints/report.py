from flask import Blueprint, Response, jsonify, request
from flask_jwt_extended import jwt_required, current_user
from sqlalchemy import func 
from models.report import Report
from models import db
from sqlalchemy.orm import defer

from models.user import User
from models.website import Site
from utils.style_generator import report_to_js
from utils.jwt import decode_jwt_token
from services.findings import latest_report_ids

report_bp = Blueprint('report', __name__)


@report_bp.route('/', methods=['GET'])
@jwt_required(optional=True)
def get_reports():
    params = request.args
    limit = params.get('limit', default=100, type=int)
    page = params.get('page', default=1, type=int)
    search = params.get('search', type=str)
    # bool("false") is True, so parse the string ourselves
    desc = params.get('desc', default='true', type=str).lower() != 'false'

    order_by = Report.timestamp.desc() if desc else Report.timestamp.asc()

    # The listing serialises without the report JSON (and the photo is deferred).
    reports_q = db.session.query(Report).options(defer(Report.report)).order_by(order_by, func.json_extract(Report.report_counts, '$.violations.total').desc())


    if search:
        reports_q = reports_q.filter(Report.url.icontains(f"%{search}%"))

    reports_q = reports_q.filter(Report.visible_to(current_user))

    reports = reports_q.paginate(page=page, per_page=limit)

    return jsonify({
        'count': reports.total,
        'items': [r.to_dict_without_report() for r in reports.items]
    }), 200

@report_bp.route('/<int:report_id>/', methods=['GET'])
@jwt_required(optional=True)
def get_report_by_id(report_id):
    report = db.session.get(Report, report_id)  
    if not report:
        return jsonify({'error': 'Report not found'}), 404
    
    if not current_user:
        if not report.public:
            return jsonify({'error': 'Unauthorized'}), 403

    if not report.can_view(current_user):
        return jsonify({'error': 'Unauthorized'}), 403

    data = report.to_dict()
    # Findings belong to the page's latest report; fingerprints may have been rebound
    # since older reports, so those carry none.
    is_latest = latest_report_ids([report.site_id]).get(report.site_id) == report.id
    data['findings'] = (
        [f.to_dict() for f in report.site.findings.filter_by(last_report_id=report.id).all()]
        if is_latest else None
    )
    data['can_edit'] = bool(current_user) and report.site.can_edit(current_user)
    return jsonify(data), 200

@report_bp.route('/<int:report_id>/pdf/', methods=['GET'])
@jwt_required(optional=True)
def get_report_pdf(report_id):
    report = db.session.get(Report, report_id)  
    if not report:
        return jsonify({'error': 'Report not found'}), 404

    if not current_user:
        if not report.public:
            return jsonify({'error': 'Unauthorized'}), 403

    if not report.can_view(current_user):
        return jsonify({'error': 'Unauthorized'}), 403

    pdf_data = report.generate_pdf()

    if not pdf_data:
        return jsonify({'error': 'Error generating PDF, Please try again later.'}), 500
    
    escaped_url = report.url.replace("/", "_").replace(":", "_")

    pdfName = f"report_{escaped_url}.pdf"

    return Response(pdf_data, mimetype='application/pdf',
                    headers={"Content-Disposition": f"attachment;filename={pdfName}"})

@report_bp.route('/script/<token>/', methods=['GET'])
def get_report_script(token):
    # Anonymous by design: the script is loaded cross-origin from the audited
    # page (DevTools console paste, or the proxy iframe), so there is no session
    # to authenticate. The unguessable signed token is the authorization, and it
    # only reaches users who can already view this (access-controlled) report.
    payload = decode_jwt_token(token)
    if payload.get('error') or payload.get('scope') != 'report-script':
        return jsonify({'error': 'Invalid token'}), 401

    report = db.session.get(Report, payload.get('report_id'))
    if not report:
        return jsonify({'error': 'Report not found'}), 404

    violation = report.report.get('violations', [])
    js_code = report_to_js(violation, report.url)

    return Response(js_code, mimetype='text/javascript')

@report_bp.route('/<int:report_id>/photo/', methods=['GET'])
@jwt_required(optional=True)
def get_report_photo(report_id):
    report = db.session.get(Report, report_id)
    if not report:
        return jsonify({'error': 'Report not found'}), 404

    if not current_user:
        if not report.public:
            return jsonify({'error': 'Unauthorized'}), 403

    if not report.can_view(current_user):
        return jsonify({'error': 'Unauthorized'}), 403

    # The column is deferred: load just the bytes, not the report JSON again.
    photo = db.session.query(Report.photo).filter(Report.id == report_id).scalar()
    if not photo:
        return jsonify({'error': 'This report has no screenshot'}), 404

    # Playwright already produced a PNG; serve it as is. A report's screenshot never
    # changes, so the browser may keep it (per user) and revalidate by ETag.
    response = Response(photo, mimetype='image/png')
    response.set_etag(f"report-{report.id}-{len(photo)}")
    response.last_modified = report.timestamp
    response.cache_control.private = True
    response.cache_control.max_age = 86400
    return response.make_conditional(request)

from flask import Blueprint, Response
from flask import request, jsonify
from flask_jwt_extended import jwt_required, current_user
from sqlalchemy import func 
from models.report import Report
from models import db
from PIL import Image
import io

from models.user import User
from models.website import Site
from utils.style_generator import report_to_js

report_bp = Blueprint('report', __name__)


@report_bp.route('/', methods=['GET'])
@jwt_required(optional=True)
def get_reports():
    params = request.args
    limit = params.get('limit', default=100, type=int)
    page = params.get('page', default=1, type=int)
    search = params.get('search', type=str)
    desc = params.get('desc', default=True, type=bool)

    order_by = Report.timestamp.desc() if desc else Report.timestamp.asc()

    reports_q = db.session.query(Report).order_by(order_by, func.json_extract(Report.report_counts, '$.violations.total').desc())


    if search:
        reports_q = reports_q.filter(Report.url.icontains(f"%{search}%"))

    if not current_user:
        reports_q = reports_q.filter(Report.public)

    if current_user:
        reports_q = reports_q.filter(Report.can_view(current_user))

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

    return jsonify(report.to_dict()), 200

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

@report_bp.route('/<int:report_id>/script/', methods=['GET'])
def get_report_script(report_id):
    # Note, Anyone can access this endpoint
    report = db.session.get(Report, report_id)  
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

    image = Image.open(io.BytesIO(report.photo))

    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)

    return Response(img_byte_arr, mimetype='image/png')

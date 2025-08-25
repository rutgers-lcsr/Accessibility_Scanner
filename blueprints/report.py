from flask import Blueprint, Response
from flask import request, jsonify
from sqlalchemy import func 
from models.report import Report
from models import db
from PIL import Image
import io

from utils.style_generator import report_to_js

report_bp = Blueprint('report', __name__)


@report_bp.route('/', methods=['GET'])
def get_reports():
    params = request.args
    limit = params.get('limit', default=100, type=int)
    page = params.get('page', default=1, type=int)
    search = params.get('search', type=str)

    reports_q = Report.query.order_by(Report.timestamp.desc(), func.json_extract(Report.report_counts, '$.violations.total').desc())

    if search:
        reports_q = reports_q.filter(Report.url.icontains(f"%{search}%"))

    reports = reports_q.paginate(page=page, per_page=limit)

    return jsonify({
        'count': reports.total,
        'items': [r.to_dict_without_report() for r in reports.items]
    }), 200

@report_bp.route('/<int:report_id>', methods=['GET'])
def get_report_by_id(report_id):
    report = db.session.get(Report, report_id)  
    if not report:
        return jsonify({'error': 'Report not found'}), 404
    return jsonify(report.to_dict()), 200

@report_bp.route('/<int:report_id>/script', methods=['GET'])
def get_report_script(report_id):
    report = db.session.get(Report, report_id)  
    if not report:
        return jsonify({'error': 'Report not found'}), 404


    violation = report.report.get('violations', [])


    js_code = report_to_js(violation)


    return js_code, 200 

@report_bp.route('/<int:report_id>/photo', methods=['GET'])
def get_report_photo(report_id):
    report = db.session.get(Report, report_id)
    if not report:
        return jsonify({'error': 'Report not found'}), 404

    image = Image.open(io.BytesIO(report.photo))

    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)

    return Response(img_byte_arr, mimetype='image/png')

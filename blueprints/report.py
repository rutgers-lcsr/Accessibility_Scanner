from flask import Blueprint
from flask import request, jsonify
from sqlalchemy import func 
from models.report import Report
from models import db
from urllib.parse import urlparse

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

@report_bp.route('/site/<string:website_url>', methods=['GET'])
def get_report(website_url):
    params = request.args

    limit = params.get('limit', default=100, type=int)
    page = params.get('page', default=1, type=int)

    # Check if str is valid url
    try:
        result = urlparse(website_url)
        if not all([result.scheme, result.netloc]):
            raise ValueError
    except ValueError:
        return jsonify({'error': 'Invalid URL'}), 400

    report = Report.query.filter(Report.url == website_url).paginate(page=page, per_page=limit)

    if not report:
        return jsonify({'error': 'Report not found'}), 404
    return jsonify({
        'count': report.total,
        'items': [r.to_dict() for r in report.items]
    }), 200
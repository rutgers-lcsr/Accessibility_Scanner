from flask import Blueprint
from flask import request, jsonify 
from models.report import Report
from urllib.parse import urlparse

report_bp = Blueprint('report', __name__,  url_prefix="/reports")


@report_bp.route('/', methods=['GET'])
def get_reports():
    params = request.args
    limit = params.get('limit', default=100, type=int)
    page = params.get('page', default=1, type=int)
    sort_by = params.get('sort_by', default='timestamp', type=str)

    reports = Report.query.order_by(getattr(Report, sort_by)).all()

    if limit:
        reports = reports[:limit]

    if page:
        reports = reports[(page - 1) * limit: page * limit]

    return jsonify([r.to_dict() for r in reports]), 200


@report_bp.route('/<string:report_id>', methods=['GET'])
def get_report(report_id):
    params = request.args

    limit = params.get('limit', default=100, type=int)
    page = params.get('page', default=1, type=int)

    # Check if str is valid url
    try:
        result = urlparse(report_id)
        if not all([result.scheme, result.netloc]):
            raise ValueError
    except ValueError:
        return jsonify({'error': 'Invalid URL'}), 400

    # Query the report
    report = Report.query.filter(Report.url.startswith(f"%{report_id}%")).all()

    if not report:
        return jsonify({'error': 'Report not found'}), 404


    if limit:
        report = report[:limit]

    if page:
        report = report[(page - 1) * limit: page * limit]

    return jsonify([r.to_dict() for r in report]), 200
from flask import Blueprint
from flask import request, jsonify 
from models.report import Report
from urllib.parse import urlparse

report_bp = Blueprint('report', __name__)


@report_bp.route('/', methods=['GET'])
def get_reports():
    params = request.args
    limit = params.get('limit', default=100, type=int)
    page = params.get('page', default=1, type=int)
    sort_by = params.get('sort_by', default='timestamp', type=str)

    reports = Report.query.order_by(getattr(Report, sort_by)).paginate(page=page, per_page=limit)

    return jsonify({
        'count': reports.total,
        'items': [r.to_dict_without_report() for r in reports.items]
    }), 200

@report_bp.route('/<int:report_id>', methods=['GET'])
def get_report_by_id(report_id):
    report = Report.query.get(report_id)
    if not report:
        return jsonify({'error': 'Report not found'}), 404
    return jsonify(report.to_dict()), 200

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
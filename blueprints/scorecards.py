"""Department scorecards and the exportable compliance report (services.scorecards).

Signed-in users see the websites they may view; site admins see every website."""
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import current_user, jwt_required

from services.scorecards import REPORT_COLUMNS, compliance_rows, department_scorecards, report_websites
from utils.export import csv_response

scorecards_bp = Blueprint('scorecards', __name__)


def _flag(name: str) -> bool:
    return (request.args.get(name) or '').lower() in ('1', 'true', 'yes')


@scorecards_bp.route('/scorecards/', methods=['GET'])
@jwt_required()
def get_scorecards():
    """
    Department scorecards over the websites the caller can view (retired ones left out),
    worst first.
    ---
    tags:
        - Reporting
    """
    rows = compliance_rows(report_websites(current_user))
    totals = department_scorecards([{**row, 'department': 'All departments'} for row in rows])
    return jsonify({
        'generated_at': datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        'departments': department_scorecards(rows),
        'totals': totals[0] if totals else None,
    }), 200


@scorecards_bp.route('/compliance-report/', methods=['GET'])
@jwt_required()
def get_compliance_report():
    """
    The compliance report: one row per website with its inventory, open issues,
    deadlines, exceptions, manual reviews, health and inventories.
    ---
    tags:
        - Reporting
    parameters:
        - in: query
          name: department
          type: string
          description: One department ("No department" for websites without one).
        - in: query
          name: include_retired
          type: boolean
        - in: query
          name: format
          type: string
          enum: [json, csv]
    """
    department = request.args.get('department') or None
    rows = compliance_rows(report_websites(current_user, department, include_retired=_flag('include_retired')))
    if request.args.get('format') == 'csv':
        name = f"compliance-report-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.csv"
        return csv_response(list(REPORT_COLUMNS), ([row.get(column) for column in REPORT_COLUMNS] for row in rows), name)
    scorecard = department_scorecards([{**row, 'department': department or 'All departments'} for row in rows])
    for row in rows:
        row.pop('fix_days', None)
    return jsonify({
        'generated_at': datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        'department': department,
        'summary': scorecard[0] if scorecard else None,
        'websites': rows,
    }), 200

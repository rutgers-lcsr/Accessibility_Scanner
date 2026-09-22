"""Triage: a person's verdict on one finding (open, fixed, false positive, accepted)."""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import current_user, jwt_required

from models import db
from models.finding import FINDING_STATUSES, Finding
from services.findings import set_finding_status

findings_bp = Blueprint('findings', __name__)


@findings_bp.route('/<int:finding_id>/', methods=['PATCH'])
@jwt_required()
def update_finding(finding_id):
    """
    Set the status (and optionally a note) of one finding.
    ---
    tags:
        - Findings
    parameters:
        - in: path
          name: finding_id
          type: integer
          required: true
        - in: body
          name: body
          required: true
          schema:
              type: object
              properties:
                  status:
                      type: string
                      enum: [open, fixed, false_positive, accepted]
                  note:
                      type: string
    responses:
        200:
            description: The updated finding.
        400:
            description: Unknown status or a note that is not text.
        403:
            description: The caller may not edit the page's website.
        404:
            description: Finding not found.
    """
    finding = db.session.get(Finding, finding_id)
    if not finding:
        return jsonify({'error': 'Finding not found'}), 404
    if not finding.site.can_edit(current_user):
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json(silent=True) or {}
    status = data.get('status')
    if status not in FINDING_STATUSES:
        return jsonify({'error': f"status must be one of {', '.join(FINDING_STATUSES)}"}), 400
    note = data.get('note')
    if note is not None and not isinstance(note, str):
        return jsonify({'error': 'note must be text'}), 400

    set_finding_status(finding, status, note, current_user.id)
    db.session.commit()
    return jsonify(finding.to_dict()), 200

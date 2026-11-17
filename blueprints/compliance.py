"""Compliance: the exceptions register and manual reviews (models.compliance).

Exceptions: website editors request them; site admins approve (normally with an expiry
date) or reject them, and see every website's in one register. Manual reviews: website
editors record them in the UI or hand an agent the prompt from .../reviews/prompt/, and
the agent submits through the API-key route in blueprints.api.
"""
from datetime import date, datetime, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import current_user, jwt_required

from authentication.login import admin_required
from config import CLIENT_URL
from models import db
from models.compliance import EXCEPTION_KINDS, ComplianceException, ManualReview
from models.website import Website
from services.reviews import agent_prompt, checklist, save_review, suggested_pages

compliance_bp = Blueprint('compliance', __name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _is_admin(user) -> bool:
    return bool(user and user.profile and user.profile.is_admin)


def _website(website_id: int, edit: bool):
    website = db.session.get(Website, website_id)
    if website is None:
        return None, (jsonify({'error': 'Website not found'}), 404)
    allowed = website.can_edit(current_user) if edit else website.can_view(current_user)
    if not current_user or not allowed:
        return None, (jsonify({'error': 'Unauthorized'}), 403)
    return website, None


def _apply_scope(exc: ComplianceException, data: dict) -> None:
    """Scope and reason fields; raises ValueError."""
    if 'kind' in data:
        if data['kind'] not in EXCEPTION_KINDS:
            raise ValueError(f"kind must be one of {', '.join(EXCEPTION_KINDS)}")
        exc.kind = data['kind']
    if 'reason' in data:
        reason = (data.get('reason') or '').strip()
        if not reason:
            raise ValueError('reason is required: say why the content cannot be fixed by its deadline')
        exc.reason = reason[:10000]
    if 'rule_id' in data:
        rule_id = (data.get('rule_id') or '').strip()
        if len(rule_id) > 100:
            raise ValueError('rule_id must be at most 100 characters')
        exc.rule_id = rule_id or None
    if 'url_prefix' in data:
        prefix = (data.get('url_prefix') or '').strip()
        if prefix:
            root = exc.website.url.rstrip('/') if exc.website else ''
            if not prefix.startswith(root):
                raise ValueError(f'url_prefix must be a page address on {root}')
        exc.url_prefix = prefix[:500] or None


def _apply_decision(exc: ComplianceException, data: dict, now: datetime) -> None:
    """Site admin fields; raises ValueError."""
    if 'expires_on' in data:
        value = data['expires_on']
        try:
            exc.expires_on = date.fromisoformat(str(value)[:10]) if value else None
        except ValueError:
            raise ValueError('expires_on must be a date (YYYY-MM-DD)')
    if 'decision_note' in data:
        exc.decision_note = (data.get('decision_note') or '').strip() or None
    if 'status' in data:
        if data['status'] not in ('requested', 'approved', 'rejected'):
            raise ValueError('status must be requested, approved or rejected')
        if data['status'] != exc.status:
            exc.status = data['status']
            exc.decided_by = current_user.id if data['status'] != 'requested' else None
            exc.decided_at = now if data['status'] != 'requested' else None


# --- exceptions --------------------------------------------------------------------------------


@compliance_bp.route('/websites/<int:website_id>/exceptions/', methods=['GET'])
@jwt_required()
def list_website_exceptions(website_id):
    """
    The website's exceptions, newest first.
    ---
    tags:
        - Compliance
    """
    website, error = _website(website_id, edit=False)
    if error:
        return error
    rows = (db.session.query(ComplianceException).filter_by(website_id=website.id)
            .order_by(ComplianceException.requested_at.desc()).all())
    return jsonify([row.to_dict() for row in rows]), 200


@compliance_bp.route('/websites/<int:website_id>/exceptions/', methods=['POST'])
@jwt_required()
def request_exception(website_id):
    """
    Request an exception (people who can edit the website). A site admin may record it
    as approved straight away by sending status and expires_on.
    ---
    tags:
        - Compliance
    parameters:
        - in: body
          name: body
          schema:
            type: object
            required: [kind, reason]
            properties:
                kind: {type: string, enum: [archived, third_party, undue_burden, fundamental_alteration, other]}
                reason: {type: string}
                rule_id: {type: string, description: One axe rule; omit for every rule.}
                url_prefix: {type: string, description: Pages starting with this address; omit for every page.}
                status: {type: string, enum: [requested, approved], description: Site admins only.}
                expires_on: {type: string, format: date, description: Site admins only.}
    """
    website, error = _website(website_id, edit=True)
    if error:
        return error
    data = request.get_json(silent=True) or {}
    for key in ('kind', 'reason'):
        if key not in data:
            return jsonify({'error': f'{key} is required'}), 400
    now = _utcnow()
    exc = ComplianceException(website=website, status='requested', requested_by=current_user.id, requested_at=now)
    try:
        _apply_scope(exc, data)
        if _is_admin(current_user):
            _apply_decision(exc, {k: v for k, v in data.items() if k in ('status', 'expires_on', 'decision_note')}, now)
    except ValueError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
    db.session.add(exc)
    db.session.commit()
    return jsonify(exc.to_dict()), 201


@compliance_bp.route('/exceptions/<int:exception_id>/', methods=['PATCH'])
@jwt_required()
def update_exception(exception_id):
    """
    Site admins decide (status, expires_on, decision_note) and may change anything;
    the website's editors may change the scope and reason while it is still requested.
    ---
    tags:
        - Compliance
    """
    exc = db.session.get(ComplianceException, exception_id)
    if exc is None:
        return jsonify({'error': 'Exception not found'}), 404
    admin = _is_admin(current_user)
    if not admin and not (exc.website.can_edit(current_user) and exc.status == 'requested'):
        return jsonify({'error': 'Unauthorized'}), 403
    data = request.get_json(silent=True) or {}
    try:
        _apply_scope(exc, data)
        if admin:
            _apply_decision(exc, data, _utcnow())
    except ValueError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
    db.session.commit()
    return jsonify(exc.to_dict()), 200


@compliance_bp.route('/exceptions/<int:exception_id>/', methods=['DELETE'])
@jwt_required()
def delete_exception(exception_id):
    """
    Withdraw a request (its website's editors) or delete any exception (site admins).
    ---
    tags:
        - Compliance
    """
    exc = db.session.get(ComplianceException, exception_id)
    if exc is None:
        return jsonify({'error': 'Exception not found'}), 404
    if not _is_admin(current_user) and not (exc.website.can_edit(current_user) and exc.status == 'requested'):
        return jsonify({'error': 'Unauthorized'}), 403
    db.session.delete(exc)
    db.session.commit()
    return '', 204


@compliance_bp.route('/exceptions/', methods=['GET'])
@admin_required
def list_all_exceptions():
    """
    The exceptions register across every website (site admins). Requested first.
    ---
    tags:
        - Compliance
    parameters:
        - in: query
          name: status
          type: string
          enum: [requested, approved, rejected, expired]
    """
    wanted = request.args.get('status')
    rows = db.session.query(ComplianceException).order_by(ComplianceException.requested_at.desc()).all()
    items = [row.to_dict() for row in rows]
    if wanted:
        items = [item for item in items if item['status'] == wanted]
    order = {'requested': 0, 'approved': 1, 'expired': 2, 'rejected': 3}
    items.sort(key=lambda item: order.get(item['status'], 4))
    return jsonify(items), 200


# --- manual reviews ------------------------------------------------------------------------------


@compliance_bp.route('/reviews/checklist/', methods=['GET'])
@jwt_required()
def get_checklist():
    """
    The manual review checklist.
    ---
    tags:
        - Reviews
    """
    return jsonify(checklist()), 200


@compliance_bp.route('/websites/<int:website_id>/reviews/', methods=['GET'])
@jwt_required()
def list_reviews(website_id):
    """
    The website's manual reviews, newest first.
    ---
    tags:
        - Reviews
    """
    website, error = _website(website_id, edit=False)
    if error:
        return error
    rows = (db.session.query(ManualReview).filter_by(website_id=website.id)
            .order_by(ManualReview.started_at.desc()).all())
    return jsonify([row.to_dict() for row in rows]), 200


@compliance_bp.route('/websites/<int:website_id>/reviews/', methods=['POST'])
@jwt_required()
def create_review(website_id):
    """
    Start (or record a finished) manual review (people who can edit the website).
    ---
    tags:
        - Reviews
    parameters:
        - in: body
          name: body
          schema:
            type: object
            properties:
                status: {type: string, enum: [in_progress, completed]}
                pages: {type: array, items: {type: string}}
                summary: {type: string}
                results: {type: object, description: '{checklist key: {result: pass|fail|not_applicable|not_tested, notes, pages}}'}
    """
    website, error = _website(website_id, edit=True)
    if error:
        return error
    now = _utcnow()
    review = ManualReview(website_id=website.id, reviewer_id=current_user.id, source='person',
                          status='in_progress', started_at=now, results={})
    try:
        save_review(review, request.get_json(silent=True) or {}, now)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    db.session.add(review)
    db.session.commit()
    return jsonify(review.to_dict()), 201


@compliance_bp.route('/websites/<int:website_id>/reviews/<int:review_id>/', methods=['PATCH'])
@jwt_required()
def update_review(website_id, review_id):
    """
    Record results on a review; results are merged item by item.
    ---
    tags:
        - Reviews
    """
    website, error = _website(website_id, edit=True)
    if error:
        return error
    review = db.session.get(ManualReview, review_id)
    if review is None or review.website_id != website.id:
        return jsonify({'error': 'Review not found'}), 404
    try:
        save_review(review, request.get_json(silent=True) or {}, _utcnow())
    except ValueError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
    db.session.commit()
    return jsonify(review.to_dict()), 200


@compliance_bp.route('/websites/<int:website_id>/reviews/<int:review_id>/', methods=['DELETE'])
@jwt_required()
def delete_review(website_id, review_id):
    """
    Delete a review (people who can edit the website).
    ---
    tags:
        - Reviews
    """
    website, error = _website(website_id, edit=True)
    if error:
        return error
    review = db.session.get(ManualReview, review_id)
    if review is None or review.website_id != website.id:
        return jsonify({'error': 'Review not found'}), 404
    db.session.delete(review)
    db.session.commit()
    return '', 204


@compliance_bp.route('/websites/<int:website_id>/reviews/prompt/', methods=['GET'])
@jwt_required()
def get_review_prompt(website_id):
    """
    Instructions for an agent to carry out the manual review and submit it with an API
    key (people who can edit the website).
    ---
    tags:
        - Reviews
    """
    website, error = _website(website_id, edit=True)
    if error:
        return error
    pages = suggested_pages(website)
    return jsonify({'pages': pages, 'prompt': agent_prompt(website, CLIENT_URL.rstrip('/'), pages)}), 200

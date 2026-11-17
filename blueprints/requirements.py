"""Content requirements (models.health.ContentRequirement): what a website's home page
must carry. Site admins define them and choose the websites each applies to; the health
check (services.health) reports whether each assigned website meets them."""
import re

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from bs4 import BeautifulSoup

from authentication.login import admin_required
from models import db
from models.health import REQUIREMENT_CHECK_TYPES, ContentRequirement
from models.website import Website

requirements_bp = Blueprint('requirements', __name__)


def _apply(requirement: ContentRequirement, data: dict) -> str | None:
    """Copy fields from ``data``; returns an error message or None."""
    if 'name' in data:
        name = (data.get('name') or '').strip()
        if not name or len(name) > 200:
            return 'name is required (at most 200 characters)'
        requirement.name = name
    if 'description' in data:
        requirement.description = (data.get('description') or '').strip() or None
    if 'check_type' in data:
        if data['check_type'] not in REQUIREMENT_CHECK_TYPES:
            return f"check_type must be one of {', '.join(REQUIREMENT_CHECK_TYPES)}"
        requirement.check_type = data['check_type']
    if 'pattern' in data:
        pattern = (data.get('pattern') or '').strip()
        if not pattern or len(pattern) > 500:
            return 'pattern is required (at most 500 characters)'
        requirement.pattern = pattern
    if 'enabled' in data:
        requirement.enabled = bool(data['enabled'])
    if 'website_ids' in data:
        ids = data['website_ids']
        if not isinstance(ids, list) or not all(isinstance(i, int) for i in ids):
            return 'website_ids must be a list of website ids'
        requirement.websites = db.session.query(Website).filter(Website.id.in_(ids)).all() if ids else []
    # The pattern must make sense for its type.
    if requirement.check_type and requirement.pattern:
        try:
            if requirement.check_type == 'selector':
                BeautifulSoup('<p></p>', 'html.parser').select_one(requirement.pattern)
            else:
                re.compile(requirement.pattern)
        except Exception as e:
            return f'Invalid pattern: {e}'
    return None


@requirements_bp.route('/', methods=['GET'])
@jwt_required()
def list_requirements():
    """
    Every content requirement with the websites it applies to.
    ---
    tags:
        - Requirements
    """
    rows = db.session.query(ContentRequirement).order_by(ContentRequirement.name).all()
    return jsonify([row.to_dict() for row in rows]), 200


@requirements_bp.route('/', methods=['POST'])
@admin_required
def create_requirement():
    """
    Create a content requirement (site admins).
    ---
    tags:
        - Requirements
    parameters:
        - in: body
          name: body
          schema:
            type: object
            required: [name, check_type, pattern]
            properties:
                name: {type: string}
                description: {type: string}
                check_type: {type: string, enum: [link_text, link_href, selector, text]}
                pattern: {type: string, description: Case-insensitive regex, or a CSS selector for check_type selector.}
                enabled: {type: boolean}
                website_ids: {type: array, items: {type: integer}}
    """
    data = request.get_json(silent=True) or {}
    for key in ('name', 'check_type', 'pattern'):
        if key not in data:
            return jsonify({'error': f'{key} is required'}), 400
    requirement = ContentRequirement(enabled=True)
    error = _apply(requirement, data)
    if error:
        return jsonify({'error': error}), 400
    db.session.add(requirement)
    db.session.commit()
    return jsonify(requirement.to_dict()), 201


@requirements_bp.route('/<int:requirement_id>/', methods=['PATCH'])
@admin_required
def update_requirement(requirement_id):
    """
    Change a content requirement or the websites it applies to (site admins).
    ---
    tags:
        - Requirements
    """
    requirement = db.session.get(ContentRequirement, requirement_id)
    if requirement is None:
        return jsonify({'error': 'Requirement not found'}), 404
    error = _apply(requirement, request.get_json(silent=True) or {})
    if error:
        db.session.rollback()
        return jsonify({'error': error}), 400
    db.session.commit()
    return jsonify(requirement.to_dict()), 200


@requirements_bp.route('/<int:requirement_id>/', methods=['DELETE'])
@admin_required
def delete_requirement(requirement_id):
    """
    Delete a content requirement (site admins).
    ---
    tags:
        - Requirements
    """
    requirement = db.session.get(ContentRequirement, requirement_id)
    if requirement is None:
        return jsonify({'error': 'Requirement not found'}), 404
    requirement.websites = []
    db.session.delete(requirement)
    db.session.commit()
    return '', 204

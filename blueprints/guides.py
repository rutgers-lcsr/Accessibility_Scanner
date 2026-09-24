"""Fix guides (services.guides): public, so a link in an email works for anyone."""
from flask import Blueprint, jsonify

from services.guides import guide_index, load_guide

guides_bp = Blueprint('guides', __name__)

CACHE_SECONDS = 300


def _cached(response):
    response.cache_control.public = True
    response.cache_control.max_age = CACHE_SECONDS
    return response


@guides_bp.route('/', methods=['GET'])
def list_guides():
    """
    The fix guides that exist, one per axe rule.
    ---
    tags:
        - Guides
    responses:
        200:
            description: count and items (rule_id, title, impact, summary), sorted by title.
    """
    items = guide_index()
    return _cached(jsonify({'count': len(items), 'items': items}))


@guides_bp.route('/<rule_id>/', methods=['GET'])
def get_guide(rule_id):
    """
    One fix guide: front matter, the common sections in order, and a tab per platform.
    ---
    tags:
        - Guides
    parameters:
        - in: path
          name: rule_id
          type: string
          required: true
    responses:
        200:
            description: The guide.
        404:
            description: No guide for this rule.
    """
    guide = load_guide(rule_id)
    if not guide:
        return jsonify({'error': 'No guide for this rule'}), 404
    return _cached(jsonify(guide))

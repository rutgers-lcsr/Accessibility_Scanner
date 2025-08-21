from flask import Blueprint, jsonify, request

from models.report import Report
from models.website import Site


sites_bp = Blueprint('sites', __name__)

@sites_bp.route('/<int:site_id>', methods=['GET'])
def get_site(site_id):
    site = Site.query.get(site_id)
    if not site:
        return jsonify({'error': 'Site not found'}), 404

    return jsonify(site.to_dict()), 200
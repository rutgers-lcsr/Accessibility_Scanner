from flask import Blueprint, jsonify, request

from models.report import Report
from models.website import Site
from models import db

sites_bp = Blueprint('sites', __name__)

@sites_bp.route('/<int:site_id>', methods=['GET'])
def get_site(site_id):
    site = db.session.get(Site, site_id)
    if not site:
        return jsonify({'error': 'Site not found'}), 404

    return jsonify(site.to_dict()), 200
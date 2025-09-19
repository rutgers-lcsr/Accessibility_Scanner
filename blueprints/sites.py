from flask import Blueprint, jsonify, request
from flask_jwt_extended import current_user, jwt_required

from models.report import Report
from models.website import Site, Website
from models import db

sites_bp = Blueprint('sites', __name__)

@sites_bp.route('/<int:site_id>/', methods=['GET'])
@jwt_required(optional=True)
def get_site(site_id):
    site = db.session.get(Site, site_id)
    if not site:
        return jsonify({'error': 'Site not found'}), 404

    if current_user:
        if not site.can_view(current_user):
            return jsonify({'error': 'Unauthorized'}), 403

    if not current_user:
        # make sure that non-admin users can only see public websites
        if site.public == False:
            return jsonify({'error': 'Unauthorized'}), 403

    return jsonify(site.to_dict()), 200
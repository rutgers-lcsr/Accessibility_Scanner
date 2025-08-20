from flask import Blueprint, jsonify, request
from models.website import Website 
from models import db
from urllib.parse import urlparse
report_bp = Blueprint('website', __name__,  url_prefix="/websites")


@report_bp.route('/', methods=['POST'])
def create_website():
    data = request.get_json()
    base_url = data.get('base_url')
    if not base_url:
        return jsonify({'error': 'Base URL is required'}), 400
    
    # Check if valid urlparse
    parsed = urlparse(base_url)
    if not all([parsed.scheme, parsed.netloc]):
        return jsonify({'error': 'Invalid URL'}), 400

    base_url = f"{parsed.scheme}://{parsed.netloc}"

    new_website = Website(base_url=base_url, last_scanned=None, active=False)

    db.session.add(new_website)
    db.session.commit()
    return jsonify(new_website.to_dict()), 201  

@report_bp.route('/', methods=['PATCH'])
def update_website():
    data = request.get_json()
    website_id = data.get('id')
    website = Website.query.get(website_id)
    if not website:
        return jsonify({'error': 'Website not found'}), 404

    # Only update fields present in the request
    for field in ['base_url', 'last_scanned', 'active']:
        if field in data:
            setattr(website, field, data[field])

    db.session.commit()
    return jsonify(website.to_dict()), 200

@report_bp.route('/', methods=['GET'])
def get_websites():
    websites = Website.query.all()
    return jsonify([w.to_dict() for w in websites]), 200


@report_bp.route('/<int:website_id>', methods=['GET'])
def get_website(website_id):
    website = Website.query.get(website_id)
    if not website:
        return jsonify({'error': 'Website not found'}), 404
    return jsonify(website.to_dict()), 200
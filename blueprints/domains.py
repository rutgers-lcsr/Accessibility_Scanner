from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import func

from authentication.login import admin_required
from models.website import Domain, Website
from models import db
from utils.urls import is_valid_domain
domain_bp = Blueprint('domain', __name__)



@domain_bp.route('/', methods=['POST'])
@admin_required 
def create_domain():
    data = request.get_json()
    domain_name = data.get('domain')
    if not domain_name:
        return jsonify({'error': 'Domain name is required'}), 400

    # check if a domain with the same name already exists
    existing_domain = db.session.query(Domain).filter(Domain.domain == domain_name).first()
    if existing_domain:
        return jsonify({'error': 'Domain already exists'}), 400


    # check if domain is valid
    if not is_valid_domain(domain_name):
        return jsonify({'error': 'Invalid domain'}), 400



    # If the domain does not exist, create a new one
    new_domain = Domain(domain=domain_name)
    db.session.add(new_domain)
    db.session.commit()

    return jsonify(new_domain.to_dict()), 201

@domain_bp.route('/', methods=['GET'])
@admin_required 
def get_domains():
    params = request.args
    page = params.get('page', 1, type=int)
    limit = params.get('limit', 10, type=int)
    search = params.get('search', type=str)

    if search:
        domains = db.session.query(Domain).filter(Domain.domain.ilike(f'%{search}%')).paginate(page=page, per_page=limit)
    else:
        domains = db.session.query(Domain).paginate(page=page, per_page=limit)
    return jsonify({
        "count": domains.total,
        "items": [domain.to_dict() for domain in domains.items]
    }), 200

@domain_bp.route('/<int:domain_id>', methods=['GET'])
@admin_required
def get_domain(domain_id):
    domain = db.session.get(Domain, domain_id)
    if not domain:
        return jsonify({'error': 'Domain not found'}), 404
    return jsonify(domain.to_dict()), 200

@domain_bp.route("/<int:domain_id>/", methods=["PATCH"])
@admin_required
def update_domain(domain_id):
    data = request.get_json()

    domain = db.session.get(Domain, domain_id)
    if not domain:
        return jsonify({'error': 'Domain not found'}), 404

    if 'domain' in data:
        domain.domain = data['domain']

    if 'active' in data:
        domain.active = data['active']
    
    
    db.session.add(domain)
    db.session.commit()
    return jsonify(domain.to_dict()), 200

@domain_bp.route('/<int:domain_id>/', methods=['DELETE'])
@admin_required
def delete_domain(domain_id):
    if not domain_id:
        return jsonify({'error': 'Domain ID is required'}), 400

    domain = db.session.get(Domain, domain_id)
    if not domain:
        return jsonify({'error': 'Domain not found'}), 404

    domain.delete()
    return jsonify({'message': 'Domain deleted successfully'}), 200
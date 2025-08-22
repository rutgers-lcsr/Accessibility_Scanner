from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from authentication.login import admin_required
from models.website import Domains
from models import db
domain_bp = Blueprint('domain', __name__)



@domain_bp.route('/', methods=['POST'])
@jwt_required()
@admin_required 
def create_domain():
    data = request.get_json()
    domain_name = data.get('domain')
    if not domain_name:
        return jsonify({'error': 'Domain name is required'}), 400

    new_domain = Domains(domain=domain_name)
    db.session.add(new_domain)
    db.session.commit()

    return jsonify(new_domain.to_dict()), 201

@domain_bp.route('/', methods=['GET'])
@jwt_required()
@admin_required 
def get_domains():
    params = request.args
    page = params.get('page', 1, type=int)
    limit = params.get('limit', 10, type=int)

    domains = Domains.query.paginate(page=page, per_page=limit)
    return jsonify([domain.to_dict() for domain in domains.items]), 200

@domain_bp.route('/', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_domain():
    data = request.get_json()
    domain_id = data.get('id')
    if not domain_id:
        return jsonify({'error': 'Domain ID is required'}), 400

    domain = db.session.get(Domains, domain_id)
    if not domain:
        return jsonify({'error': 'Domain not found'}), 404

    db.session.delete(domain)
    db.session.commit()
    return jsonify({'message': 'Domain deleted successfully'}), 200
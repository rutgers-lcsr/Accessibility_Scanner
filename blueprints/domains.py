from flask import Blueprint, jsonify, request
from flask_login import login_required

from authentication.login import user_is_admin
from models.website import Domains
from models import db
domain_bp = Blueprint('domain', __name__)


@domain_bp.route('/', methods=['POST'])
@login_required
@user_is_admin
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
def get_domains():
    params = request.args
    page = params.get('page', 1, type=int)
    limit = params.get('limit', 10, type=int)

    domains = Domains.query.paginate(page=page, per_page=limit)
    return jsonify([domain.to_dict() for domain in domains.items]), 200
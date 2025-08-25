from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import func

from authentication.login import admin_required
from models.website import Domains, Website
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
    existing_domain = db.session.query(Domains).filter(Domains.domain == domain_name).first()
    if existing_domain:
        return jsonify({'error': 'Domain already exists'}), 400


    # check if domain is valid
    if not is_valid_domain(domain_name):
        return jsonify({'error': 'Invalid domain'}), 400



    # If the domain does not exist, create a new one
    new_domain = Domains(domain=domain_name)
    db.session.add(new_domain)

    # check if a parent domain exists

        
    # check if this domain has children
    all_domains = db.session.query(Domains).all()
    for domain in all_domains:
        print(domain.domain)
        if domain.domain == new_domain.domain:
            # use domain because id might not exist yet
            # prevent cyclic relationships
            continue


        # check if new domain is a subdomain of an existing domain
        if new_domain.domain.endswith(domain.domain):
            new_domain.parent = domain                          
            break
        # check if new domain is a parent of an existing domain
        if domain.domain.endswith(new_domain.domain):
            domain.parent = new_domain
            db.session.add(domain)

    websites = db.session.query(Website).filter(Website.base_url.like(f'%{domain_name}%')).all()
    for website in websites:
        
        if website.domain_id:
            # website is already on a domain, check if the domain requested is a subdomain,
            # if it is a subdomain, then the website becomes attached to the new domain
            # if the new domain is a parent domain, then we assume that the sub domain has control of the website, and continue
            current_website_domain = website.domain
            if domain_name.endswith(current_website_domain.domain):
                # the domain is a subdomain of the original website domain, therefore change control to the subdomain. this allows for more presise control of the websites. 
                
                website.domain_id = new_domain.id
                website.domain = new_domain
                website.domain.parent = current_website_domain
            elif current_website_domain.domain.endswith(domain_name):
                # the current website domain is a subdomain of the new domain,
                # therefore, add the parent relationship, but keep the current website domain as the child
                current_website_domain.parent = new_domain
                
            else:
                # If we get here then somehow the domains are not related and bytes have flipped or something
                continue
            
        website.domain_id = new_domain.id
        website.domain = new_domain
        db.session.add(website)

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
        domains = Domains.query.filter(Domains.domain.ilike(f'%{search}%')).paginate(page=page, per_page=limit)
    else:
        domains = Domains.query.paginate(page=page, per_page=limit)
    return jsonify({
        "count": domains.total,
        "items": [domain.to_dict() for domain in domains.items]
    }), 200

@domain_bp.route('/<int:domain_id>', methods=['GET'])
@admin_required
def get_domain(domain_id):
    domain = db.session.get(Domains, domain_id)
    if not domain:
        return jsonify({'error': 'Domain not found'}), 404
    return jsonify(domain.to_dict()), 200

@domain_bp.route("/<int:domain_id>", methods=["PATCH"])
@admin_required
def update_domain(domain_id):
    data = request.get_json()
    
    domain = db.session.get(Domains, domain_id)
    if not domain:
        return jsonify({'error': 'Domain not found'}), 404

    if 'domain' in data:
        domain.domain = data['domain']

    if 'active' in data:
        domain.active = data['active']
    
    
    db.session.add(domain)
    db.session.commit()
    return jsonify(domain.to_dict()), 200

@domain_bp.route('/<int:domain_id>', methods=['DELETE'])
@admin_required
def delete_domain(domain_id):
    if not domain_id:
        return jsonify({'error': 'Domain ID is required'}), 400

    domain = db.session.get(Domains, domain_id)
    if not domain:
        return jsonify({'error': 'Domain not found'}), 404

    db.session.delete(domain)
    db.session.commit()
    return jsonify({'message': 'Domain deleted successfully'}), 200
"""The vendor register (models.inventory.Vendor): third parties the websites rely on,
with their accessibility conformance reports (VPAT/ACR) and review dates. Signed-in
users can read it; site admins maintain it."""
import re
from datetime import date

from flask import Blueprint, jsonify, request
from flask_jwt_extended import current_user, jwt_required

from authentication.login import admin_required
from models import db
from models.inventory import VENDOR_STATUSES, Vendor
vendors_bp = Blueprint('vendors', __name__)

# A host name by syntax only (no DNS lookup: a vendor entry is a suffix to match).
HOST_NAME = re.compile(r'^(?=.{1,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$')


def _date(value, key: str):
    if value in (None, ''):
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        raise ValueError(f'{key} must be a date (YYYY-MM-DD)')


def _apply(vendor: Vendor, data: dict) -> None:
    """Copy fields from ``data``; raises ValueError for an invalid value."""
    if 'name' in data:
        name = (data.get('name') or '').strip()
        if not name or len(name) > 200:
            raise ValueError('name is required (at most 200 characters)')
        vendor.name = name
    if 'hosts' in data:
        hosts = data['hosts']
        if isinstance(hosts, str):
            hosts = hosts.split()
        if not isinstance(hosts, list):
            raise ValueError('hosts must be a list of host names')
        cleaned = []
        for host in hosts:
            host = str(host).strip().lower().lstrip('.')
            if not host:
                continue
            if not HOST_NAME.match(host):
                raise ValueError(f"'{host}' is not a host name")
            if host not in cleaned:
                cleaned.append(host)
        vendor.hosts = '\n'.join(cleaned)
    if 'status' in data:
        if data['status'] not in VENDOR_STATUSES:
            raise ValueError(f"status must be one of {', '.join(VENDOR_STATUSES)}")
        vendor.status = data['status']
    for key, length in (('vpat_url', 1000), ('contact', 300)):
        if key in data:
            value = (data.get(key) or '').strip()
            if len(value) > length:
                raise ValueError(f'{key} must be at most {length} characters')
            if key == 'vpat_url' and value and not value.lower().startswith(('http://', 'https://')):
                raise ValueError('vpat_url must be an http(s) address')
            setattr(vendor, key, value or None)
    if 'notes' in data:
        vendor.notes = (data.get('notes') or '').strip() or None
    if 'vpat_date' in data:
        vendor.vpat_date = _date(data['vpat_date'], 'vpat_date')
    if 'review_due' in data:
        vendor.review_due = _date(data['review_due'], 'review_due')


@vendors_bp.route('/', methods=['GET'])
@jwt_required()
def list_vendors():
    """
    Every vendor with how many websites use it, and which of those the caller may see
    (``sites``: url, the vendor's hosts it uses, pages, kinds).
    ---
    tags:
        - Vendors
    """
    from services.inventory import vendor_sites, vendor_usage  # local import: services import models
    usage = vendor_usage()
    sites = vendor_sites(lambda website: website.can_view(current_user))
    vendors = db.session.query(Vendor).order_by(Vendor.name).all()
    return jsonify([{**vendor.to_dict(), 'websites': usage.get(vendor.id, 0), 'sites': sites.get(vendor.id, [])}
                    for vendor in vendors]), 200


@vendors_bp.route('/unassigned-hosts/', methods=['GET'])
@admin_required
def list_unassigned_hosts():
    """
    Third-party hosts seen on the websites that match no vendor, most used first.
    ---
    tags:
        - Vendors
    """
    from services.inventory import unassigned_hosts  # local import: services import models
    return jsonify(unassigned_hosts()), 200


@vendors_bp.route('/', methods=['POST'])
@admin_required
def create_vendor():
    """
    Add a vendor (site admins).
    ---
    tags:
        - Vendors
    parameters:
        - in: body
          name: body
          schema:
            type: object
            required: [name]
            properties:
                name: {type: string}
                hosts: {type: array, items: {type: string}, description: Host names; subdomains match too.}
                status: {type: string, enum: [approved, under_review, not_approved]}
                vpat_url: {type: string}
                vpat_date: {type: string, format: date}
                review_due: {type: string, format: date}
                contact: {type: string}
                notes: {type: string}
    """
    data = request.get_json(silent=True) or {}
    if 'name' not in data:
        return jsonify({'error': 'name is required'}), 400
    vendor = Vendor(hosts='', status='under_review')
    try:
        _apply(vendor, data)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    db.session.add(vendor)
    db.session.commit()
    return jsonify(vendor.to_dict()), 201


@vendors_bp.route('/<int:vendor_id>/', methods=['PATCH'])
@admin_required
def update_vendor(vendor_id):
    """
    Change a vendor (site admins).
    ---
    tags:
        - Vendors
    """
    vendor = db.session.get(Vendor, vendor_id)
    if vendor is None:
        return jsonify({'error': 'Vendor not found'}), 404
    try:
        _apply(vendor, request.get_json(silent=True) or {})
    except ValueError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
    db.session.commit()
    return jsonify(vendor.to_dict()), 200


@vendors_bp.route('/<int:vendor_id>/', methods=['DELETE'])
@admin_required
def delete_vendor(vendor_id):
    """
    Delete a vendor (site admins). Its hosts show up as unassigned again.
    ---
    tags:
        - Vendors
    """
    vendor = db.session.get(Vendor, vendor_id)
    if vendor is None:
        return jsonify({'error': 'Vendor not found'}), 404
    db.session.delete(vendor)
    db.session.commit()
    return '', 204

from flask import Blueprint, jsonify, request
from flask_jwt_extended import current_user, jwt_required

from models import db
from models.api_key import ApiKey

api_keys_bp = Blueprint('api_keys', __name__)


@api_keys_bp.route('/', methods=['GET'])
@jwt_required()
def list_api_keys():
    keys = (
        db.session.query(ApiKey)
        .filter_by(user_id=current_user.id, revoked=False)
        .order_by(ApiKey.created_at.desc())
        .all()
    )
    return jsonify([k.to_dict() for k in keys]), 200


@api_keys_bp.route('/', methods=['POST'])
@jwt_required()
def create_api_key():
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'A name is required'}), 400

    api_key, token = ApiKey.create(current_user, name)
    # The plaintext key is returned only here and never again.
    return jsonify({**api_key.to_dict(), 'key': token}), 201


@api_keys_bp.route('/<int:key_id>/', methods=['DELETE'])
@jwt_required()
def revoke_api_key(key_id):
    api_key = db.session.get(ApiKey, key_id)
    if not api_key or api_key.user_id != current_user.id:
        return jsonify({'error': 'API key not found'}), 404

    api_key.revoked = True
    db.session.commit()
    return jsonify({'message': 'API key revoked'}), 200

from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required
from models.user import User
from models import db
from models.website import Website
from utils.jwt import decode_jwt_token

user_bp = Blueprint('user', __name__)

@user_bp.route('/me', methods=['GET'])
@jwt_required()
def get_user():
    user = db.session.get(User, get_jwt_identity())
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify(user.to_dict()), 200
    

@user_bp.route('/unsubscribe', methods=['GET'])
def unsubscribe():
    
    # This token is created in NewWebsiteEmail
    token = request.args.get('token')
    if not token:
        return jsonify({'error': 'Token is required'}), 400

    email = decode_jwt_token(token)
    if not email or email.get("error", None) is not None:
        return jsonify({'error': 'Invalid token'}), 401

    website = db.session.query(Website).filter_by(email=email['email'], id=email['website_id']).first()
    if not website:
        return jsonify({'error': 'Website not found'}), 404

    website.should_email = False
    db.session.commit()

    return jsonify({'message': 'You have been unsubscribed from email notifications.'}), 200
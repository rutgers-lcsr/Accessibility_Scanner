from flask import Blueprint, app, redirect, request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, current_user, get_jwt_identity, jwt_required, unset_jwt_cookies
from models.user import User
from models import db
from werkzeug.security import check_password_hash

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/token', methods=['POST'])
def token():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    user = db.session.query(User).filter_by(email=email).first()
    if user and check_password_hash(user.password, password):
        access_token = create_access_token(identity=user)
        refresh_token = create_refresh_token(identity=user)
        return jsonify({**user.to_dict(), 'access_token': access_token, 'refresh_token': refresh_token}), 200

    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    return jsonify({'error': 'Invalid email or password'}), 401

@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    access_token = create_access_token(identity=current_user)
    return jsonify(access_token=access_token), 200

@auth_bp.route("/logout")
@jwt_required()
def logout():
    unset_jwt_cookies()
    return jsonify({'message': 'Logged out successfully'}), 200

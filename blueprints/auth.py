from flask import Blueprint, app, redirect, request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, current_user, jwt_required, unset_jwt_cookies, set_access_cookies, set_refresh_cookies
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
        
        
        
        
        response = jsonify({**user.to_dict(), 'access_token': access_token, 'refresh_token': refresh_token})
        set_access_cookies(response, access_token)
        set_refresh_cookies(response, refresh_token)

        return response, 200

    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    return jsonify({'error': 'Invalid email or password'}), 401

@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    access_token = create_access_token(identity=current_user)
    return jsonify(access_token=access_token), 200

@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    response = jsonify({"msg": "logout successful"})
    unset_jwt_cookies(response)
    return response, 200

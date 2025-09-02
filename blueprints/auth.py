from flask import Blueprint, app, json, redirect, request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, current_user, jwt_required, unset_jwt_cookies, set_access_cookies, set_refresh_cookies
from authentication.permissions import is_site_admin
from models.user import User
from models import db
from werkzeug.security import check_password_hash
auth_bp = Blueprint('auth', __name__)


@auth_bp.route("/cas", methods=["GET"])
def cas_login():
    """CAS login endpoint

    This endpoint is used to log in users via CAS (Central Authentication Service).

    x-cas-user: The user to log in (must be set by the frontend)
    x-cas-server: The CAS server to authenticate against (must be set by the frontend)
    """

    # cas login happens on the frontend, and the frontend then adds a header x-cas-user defining the user
    cas_user = request.headers.get('x-cas-user')

    if cas_user is None:
        return jsonify({'error': 'CAS user missing'}), 400
    
    cas_server = request.headers.get('x-cas-server')

    if cas_server is None:
        return jsonify({'error': 'CAS server missing'}), 400

    netloc = cas_server.split("//")[-1].split("/")[0].split('.')

    # get domain of cas server
    cas_server_domain = netloc[-2] + '.' + netloc[-1]

    # assume user email is <cas_user>@<cas_server_domain>
    user_email = cas_user + '@' + cas_server_domain

    user = db.session.query(User).filter_by(email=user_email).first()
    if user:
        # Create a JWT token for the user
        access_token = create_access_token(identity=user)
        refresh_token = create_refresh_token(identity=user)
        response = jsonify(**user.to_dict(), access_token=access_token, refresh_token=refresh_token)
        set_access_cookies(response, access_token)
        set_refresh_cookies(response, refresh_token)
        return response, 200
    else:
        # check if user is admin
        if is_site_admin(cas_user):
            user = User(email=user_email)
            user.profile.is_admin = True
            db.session.add(user)
            db.session.commit()
            # Create a JWT token for the user
            access_token = create_access_token(identity=user)
            refresh_token = create_refresh_token(identity=user)
            response = jsonify(**user.to_dict(), access_token=access_token, refresh_token=refresh_token)
            set_access_cookies(response, access_token)
            set_refresh_cookies(response, refresh_token)
            return response, 200
        else:
            user = User(email=user_email)
            db.session.add(user)
            db.session.commit()
            # Create a JWT token for the user
            access_token = create_access_token(identity=user)
            refresh_token = create_refresh_token(identity=user)
            response = jsonify(**user.to_dict(), access_token=access_token, refresh_token=refresh_token)
            set_access_cookies(response, access_token)
            set_refresh_cookies(response, refresh_token)
            return response, 200

    return jsonify({'error': 'User not found'}), 404

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
    response = jsonify(access_token=access_token)
    set_access_cookies(response, access_token)
    return response, 200

@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    response = jsonify({"msg": "logout successful"})
    unset_jwt_cookies(response)
    return response, 200

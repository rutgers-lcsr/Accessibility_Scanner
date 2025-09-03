import datetime
from urllib.parse import urlparse
from flask import Blueprint, app, json, redirect, request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, current_user, jwt_required, unset_jwt_cookies, set_access_cookies, set_refresh_cookies
from authentication.permissions import is_site_admin
from models.user import Profile, User
from models import db
from werkzeug.security import check_password_hash
auth_bp = Blueprint('auth', __name__)


def get_domain_from_netloc(netloc):
    if not netloc:
        return None

    if ':' in netloc:
        netloc = netloc.split(':')[0]

    parts = netloc.split('.')

    if len(parts) > 2:
        return parts[-2] + '.' + parts[-1]
    return netloc

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

    netloc = urlparse(cas_server).netloc

    # get domain of cas server
    cas_server_domain = get_domain_from_netloc(netloc)

    # assume user email is <cas_user>@<cas_server_domain>
    user_email = cas_user + '@' + cas_server_domain

    user = db.session.query(User).filter_by(username=cas_user).first()
    if user:
        # Create a JWT token for the user
        access_token = create_access_token(identity=user, expires_delta=datetime.timedelta(hours=24))
        response = jsonify(**user.to_dict(), access_token=access_token)
        set_access_cookies(response, access_token)
        return response, 200
    else:
        user = User(username=cas_user, email=user_email)
        user.profile = Profile(user=user, is_admin=is_site_admin(cas_user)) 
        db.session.add(user)
        db.session.commit()
        # Create a JWT token for the user
        access_token = create_access_token(identity=user, expires_delta=datetime.timedelta(hours=24))
        response = jsonify(**user.to_dict(), access_token=access_token)
        set_access_cookies(response, access_token)
        return response, 200

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

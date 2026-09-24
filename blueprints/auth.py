import hmac
from urllib.parse import urlparse
from datetime import datetime, timezone
from flask import Blueprint, current_app, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required
from authentication.permissions import is_site_admin
from models.user import Profile, User
from models import db
from utils.limiter import limiter
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
@limiter.limit("60/minute")
def cas_login():
    """CAS login endpoint

    This endpoint is used to log in users via CAS (Central Authentication Service).

    x-cas-user: The user to log in (must be set by the frontend)
    x-cas-server: The CAS server to authenticate against (must be set by the frontend)
    X-Internal-Secret: shared secret proving the request comes from the frontend proxy
    """

    # The identity headers are trusted, so only the Next.js proxy (which has validated
    # the CAS ticket) may call this. Anything else on the network gets a 403.
    secret = current_app.config.get("INTERNAL_AUTH_SECRET") or ""
    provided = request.headers.get("X-Internal-Secret", "")
    if not secret or not hmac.compare_digest(provided, secret):
        return jsonify({'error': 'Forbidden'}), 403

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
    if not user:
        user = User(username=cas_user, email=user_email)
        user.profile = Profile(user=user, is_admin=is_site_admin(user_email))
        db.session.add(user)
        db.session.commit()
    user.last_login = datetime.now(timezone.utc).replace(tzinfo=None)
    db.session.commit()

    # Lifetime comes from JWT_ACCESS_TOKEN_EXPIRES in config.py. The token is returned in
    # the body only; the Next.js proxy stores it in its own session and sends it as a
    # bearer header on every request.
    access_token = create_access_token(identity=user)
    return jsonify(**user.to_dict(), access_token=access_token), 200

@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    # Tokens are only ever carried in the Authorization header, so there is no
    # server-side state to clear; the client simply discards its token.
    return jsonify({"msg": "logout successful"}), 200

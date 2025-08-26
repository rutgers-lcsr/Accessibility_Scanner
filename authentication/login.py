from functools import wraps
from flask import jsonify
from flask_jwt_extended import current_user, jwt_required, decode_token,get_jwt,JWTManager

from models.user import User
from models import db
# Helper functions for authentication

jwt = JWTManager()

@jwt.user_identity_loader
def user_identity_lookup(user):
    return str(user.id)

@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data):
    identity = int(jwt_data["sub"])
    return db.session.get(User, identity)


def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        if not current_user or not current_user.profile or not current_user.profile.is_admin:
            return jsonify({"msg": "Unauthorized"}), 403
        return fn(*args, **kwargs)
    return wrapper
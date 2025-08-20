from flask import Blueprint, request, jsonify
from flask_login import current_user, login_required

from authentication.login import user_is_admin
from models.user import User


user_bp = Blueprint('user', __name__)

@user_bp.route('/me', methods=['GET'])
@login_required
def get_user():
    user = User.query.get(current_user.id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify(user.to_dict()), 200
    

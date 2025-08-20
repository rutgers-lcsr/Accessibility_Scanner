from flask import Blueprint, app, redirect, request, jsonify
from flask_login import login_required, login_user, logout_user

from models.user import User
from authentication.login import login_manager
from werkzeug.security import generate_password_hash, check_password_hash

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password, password):
        login_user(user)
        return jsonify(user.to_dict()), 200
    
    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    return jsonify({'error': 'Invalid username or password'}), 401

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return jsonify({'message': 'Logged out successfully'}), 200


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
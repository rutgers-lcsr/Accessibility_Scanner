from flask import jsonify
from flask_login import LoginManager

from models.user import User

login_manager = LoginManager()


# Helper functions for authentication

def user_is_admin(func):
    def wrapper(*args, **kwargs):
        user = kwargs.get('user')
        if user and user.is_authenticated and user.profile.is_admin:
            return func(*args, **kwargs)
        return jsonify({'error': 'Unauthorized'}), 403
    return wrapper

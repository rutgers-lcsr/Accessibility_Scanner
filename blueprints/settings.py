

from flask import Blueprint
from authentication.login import admin_required
from models.settings import Settings


settings_bp = Blueprint('settings', __name__)


from flask import request, jsonify
from flask_jwt_extended import jwt_required, current_user



@settings_bp.route('/', methods=['GET'])
@admin_required
def get_settings():
    settings = Settings.to_dict()
    return jsonify(settings), 200

@settings_bp.route('/', methods=['PUT'])
@admin_required
def update_settings():
    data = request.json
    for key, value in data.items():
        if key in ['default_tags', 'default_rate_limit', 'default_should_auto_scan', 'default_notify_on_completion', 'default_email_domain']:
            Settings.set(key, str(value))
    updated_settings = Settings.to_dict()
    return jsonify(updated_settings), 200
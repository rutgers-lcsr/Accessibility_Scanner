

from flask import Blueprint
from authentication.login import admin_required
from models.settings import APP_SETTINGS, Settings


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
    updated = False
    for key, value in data.items():
        if key in APP_SETTINGS:
            Settings.set(key, str(value))
            updated = True
    updated_settings = Settings.to_dict()
    if not updated:
        return jsonify({"message": "No valid settings provided."}), 400
    return jsonify(updated_settings), 200
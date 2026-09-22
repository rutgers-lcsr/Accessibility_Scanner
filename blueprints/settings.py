import re

from flask import Blueprint, jsonify, request

from authentication.login import admin_required
from models.settings import APP_SETTINGS, Settings

settings_bp = Blueprint('settings', __name__)

_HOSTNAME = re.compile(r'^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$', re.I)
_TAG = re.compile(r'^[A-Za-z0-9_.*-]+$')


def _int_at_least(minimum):
    def check(value):
        try:
            number = int(str(value).strip())
        except (TypeError, ValueError):
            return None, "must be a whole number"
        if number < minimum:
            return None, f"must be at least {minimum}"
        return str(number), None
    return check


def _boolean(value):
    text = str(value).strip().lower()
    if text in ("true", "false"):
        return text, None
    return None, "must be true or false"


def _hostname_or_empty(value):
    text = str(value).strip().lower()
    if text == "" or _HOSTNAME.match(text):
        return text, None
    return None, "must be a hostname such as rutgers.edu"


def _tag_list(value):
    tags = [t.strip() for t in str(value).split(",") if t.strip()]
    bad = [t for t in tags if not _TAG.match(t)]
    if bad:
        return None, f"invalid tag(s): {', '.join(bad)}"
    return ", ".join(tags), None


# Each validator returns (normalised value, None) or (None, reason).
VALIDATORS = {
    "default_tags": _tag_list,
    "default_rate_limit": _int_at_least(1),
    "default_should_auto_scan": _boolean,
    "default_should_auto_activate": _boolean,
    "default_notify_on_completion": _boolean,
    "default_email_domain": _hostname_or_empty,
    "scan_page_concurrency": _int_at_least(1),
    "max_pages": _int_at_least(1),
    "max_depth": _int_at_least(0),
    "crawl_delay_ms": _int_at_least(0),
    "admin_digest_enabled": _boolean,
    "retention_enabled": _boolean,
    "retention_keep_days": _int_at_least(1),
    "retention_max_days": _int_at_least(1),
}


@settings_bp.route('/', methods=['GET'])
@admin_required
def get_settings():
    settings = Settings.to_dict()
    return jsonify(settings), 200


@settings_bp.route('/', methods=['PUT'])
@admin_required
def update_settings():
    data = request.get_json(silent=True) or {}
    accepted = {}
    for key, value in data.items():
        if key not in APP_SETTINGS:
            continue
        validate = VALIDATORS.get(key)
        if validate is None:
            accepted[key] = str(value)
            continue
        normalised, reason = validate(value)
        if reason:
            return jsonify({"error": f"{key} {reason}"}), 400
        accepted[key] = normalised

    if not accepted:
        return jsonify({"message": "No valid settings provided."}), 400
    for key, value in accepted.items():
        Settings.set(key, value)
    return jsonify(Settings.to_dict()), 200

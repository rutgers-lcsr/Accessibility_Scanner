from functools import wraps

from flask import g, jsonify, request

from models.api_key import ApiKey


def _extract_token() -> str | None:
    """Read the API key from the X-API-Key header or an Authorization Bearer header."""
    token = request.headers.get('X-API-Key')
    if token:
        return token.strip()

    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        return auth[len('Bearer '):].strip()

    return None


def api_key_required(fn):
    """Authenticate a request via an API key.

    On success the owning user is available as ``g.api_user``.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = _extract_token()
        api_key = ApiKey.verify(token)
        if not api_key:
            return jsonify({"error": "Invalid or missing API key"}), 401

        api_key.touch()
        g.api_user = api_key.user
        return fn(*args, **kwargs)
    return wrapper

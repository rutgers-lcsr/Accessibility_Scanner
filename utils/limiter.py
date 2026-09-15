"""Application-wide rate limiter (Flask-Limiter).

Every request from the browser reaches Flask through the Next.js proxy, so keying on
the client address would put all users in one bucket. Requests are keyed by the
authenticated identity instead (JWT subject, then API key), falling back to the
address for anonymous calls. Storage and enablement come from RATELIMIT_* in config.py.
"""
import hashlib

from flask import request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


def rate_limit_key() -> str:
    try:
        verify_jwt_in_request(optional=True)
        identity = get_jwt_identity()
        if identity:
            return f"user:{identity}"
    except Exception:
        # Not a JWT (or an invalid one); the view's own decorator will reject it.
        pass

    auth = request.headers.get("Authorization", "")
    token = request.headers.get("X-API-Key") or (auth[len("Bearer "):] if auth.startswith("Bearer ") else "")
    if token:
        return "key:" + hashlib.sha256(token.encode()).hexdigest()[:16]

    return "ip:" + get_remote_address()


limiter = Limiter(key_func=rate_limit_key)

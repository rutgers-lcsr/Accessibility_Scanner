import os
from datetime import timedelta

TESTING = os.environ.get("TESTING", "False") == "True"


def _require(name: str) -> str:
    """Return a required environment variable, failing fast at startup when it is unset.

    Under TESTING a placeholder is returned so the test suite needs no real secrets.
    """
    value = os.environ.get(name)
    if value:
        return value
    if os.environ.get("TESTING", "False") == "True":
        return f"testing-only-placeholder-value-for-{name.lower()}"
    raise RuntimeError(
        f"{name} is not set. Export it (or add it to .env, see .env.example) before starting the app."
    )


SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///audit.db")
SQLALCHEMY_TRACK_MODIFICATIONS = False

# SQLite-specific settings for better concurrent access
if SQLALCHEMY_DATABASE_URI.startswith("sqlite"):
    SQLALCHEMY_ENGINE_OPTIONS = {
        'connect_args': {
            'timeout': 30,  # 30 second timeout for database locks
            'check_same_thread': False  # Allow sharing connection across threads
        },
        'pool_pre_ping': True,  # Verify connections before using
        'pool_recycle': 3600,  # Recycle connections after 1 hour
    }
else:
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 3600,
    }

DEBUG = os.environ.get("DEBUG", "False") == "True"
FLASK_ENV = os.environ.get("FLASK_ENV", "development")
JWT_SECRET_KEY = _require("JWT_SECRET_KEY")
# Tokens travel in the Authorization header only; the Next.js proxy attaches it server-side.
JWT_TOKEN_LOCATION = ['headers']
JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)

SITE_ADMINS = [admin.strip() for admin in os.environ.get("SITE_ADMINS", "").split(",") if admin.strip()]

HOSTNAME = os.environ.get("HOSTNAME", "localhost")
CLIENT_URL = os.environ.get("CLIENT_URL", "http://localhost:3000")
MAIL_SERVER = os.environ.get("MAIL_SERVER", "mx.farside.rutgers.edu")
MAIL_PORT = os.environ.get("MAIL_PORT", 25)
MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "help@cs.rutgers.edu")
MAIL_USE_SSL = os.environ.get("MAIL_USE_SSL", "False") == "True"
MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "True") == "True"

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/1")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")


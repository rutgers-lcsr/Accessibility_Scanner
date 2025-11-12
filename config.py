import os
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

DEBUG = os.environ.get("DEBUG", "True") == "True"
FLASK_ENV = os.environ.get("FLASK_ENV", "development")
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "KHJADoishdjfo")
JWT_TOKEN_LOCATION = ['headers', 'cookies']

SITE_ADMINS = os.environ.get("SITE_ADMINS", "mk1800@rutgers.edu").split(",")

HOSTNAME = os.environ.get("HOSTNAME", "localhost")
CLIENT_URL = os.environ.get("CLIENT_URL", "http://localhost:3000")
TESTING = os.environ.get("TESTING", "False") == "True"
MAIL_SERVER = os.environ.get("MAIL_SERVER", "mx.farside.rutgers.edu")
MAIL_PORT = os.environ.get("MAIL_PORT", 25)
MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "help@cs.rutgers.edu")
MAIL_USE_SSL = os.environ.get("MAIL_USE_SSL", "False") == "True"
MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "True") == "True"

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/1")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")


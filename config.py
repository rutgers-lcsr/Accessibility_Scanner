import os
SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///audit.db")
SQLALCHEMY_TRACK_MODIFICATIONS = False
TESTING = True
DEBUG = os.environ.get("DEBUG", "True") == "True"
FLASK_ENV = os.environ.get("FLASK_ENV", "development")
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "KHJADoishdjfo")
HOSTNAME = os.environ.get("HOSTNAME", "localhost")
CLIENT_URL = os.environ.get("CLIENT_URL", "http://localhost:3000")
MAIL_SERVER = os.environ.get("MAIL_SERVER", "mx.farside.rutgers.edu")
MAIL_PORT = os.environ.get("MAIL_PORT", 25)
MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "help@cs.rutgers.edu")
MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "True") == "True"
MAIL_USE_SSL = os.environ.get("MAIL_USE_SSL", "False") == "True"
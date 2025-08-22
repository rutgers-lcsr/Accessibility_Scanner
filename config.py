import os
SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///audit.db")
SQLALCHEMY_TRACK_MODIFICATIONS = False
TESTING = True
DEBUG = os.environ.get("DEBUG", "True") == "True"
FLASK_ENV = os.environ.get("FLASK_ENV", "development")
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "KHJADoishdjfo")
HOSTNAME = os.environ.get("HOSTNAME", "localhost")


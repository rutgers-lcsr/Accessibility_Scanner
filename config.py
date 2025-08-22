import os
SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///audit.db")
SQLALCHEMY_TRACK_MODIFICATIONS = False
TESTING = True
DEBUG = os.environ.get("DEBUG", "True") == "True"
FLASK_ENV = os.environ.get("FLASK_ENV", "development")
SECRET_KEY = os.environ.get("SECRET_KEY", "KHJADoishdjfo")
HOSTNAME = os.environ.get("HOSTNAME", "localhost")
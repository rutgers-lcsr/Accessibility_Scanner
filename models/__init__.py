from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData
from config import SQLALCHEMY_DATABASE_URI


if SQLALCHEMY_DATABASE_URI.startswith("sqlite"):
    db = SQLAlchemy()
else:
    db = SQLAlchemy(metadata=MetaData(schema="a11y"))
    
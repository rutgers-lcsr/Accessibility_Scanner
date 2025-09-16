from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData
from config import SQLALCHEMY_DATABASE_URI
from .user import *
from .website import *
from .report import *
from .rules import *
from .settings import *
from .utils import *

if SQLALCHEMY_DATABASE_URI.startswith("sqlite"):
    db = SQLAlchemy()
else:
    db = SQLAlchemy(metadata=MetaData(schema="a11y"))
    
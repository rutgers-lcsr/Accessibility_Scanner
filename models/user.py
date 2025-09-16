from typing import List
from models import db
from sqlalchemy.ext.hybrid import hybrid_method
from sqlalchemy.orm import Mapped
from datetime import datetime

# Use string-based type hint to avoid circular import
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from models.website import Website

class User(db.Model):
    __tablename__ = 'users'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    username: Mapped[str] = db.Column(db.String(255), unique=True, nullable=False)
    email: Mapped[str] = db.Column(db.String(255), unique=True, nullable=False)
    # Use string-based relationship to avoid circular import
    websites: Mapped[List["Website"]] = db.relationship("Website", back_populates='user', lazy=True)
    # password is nullable because users can login using cas
    password: Mapped[str] = db.Column(db.String(255), nullable=True)
    is_active: Mapped[bool] = db.Column(db.Boolean, default=True)
    created_at: Mapped[datetime] = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at: Mapped[datetime] = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    profile: Mapped['Profile'] = db.relationship('Profile', backref='user', lazy=True, uselist=False)

    @hybrid_method
    def get_id(self):
        return self.id

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'is_admin': self.profile.is_admin if self.profile else False,
            'is_active': self.is_active,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


    def __init__(self, username, email):
        self.username = username
        self.email = email

    def __repr__(self):
        return f'<User {self.email}>'


class Profile(db.Model):
    __tablename__ = 'profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())


    def __init__(self, user, is_admin=False):
        self.user = user
        self.is_admin = is_admin

    def __repr__(self):
        return f'<Profile {self.user_id}>'
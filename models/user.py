from models import db
from sqlalchemy.ext.hybrid import hybrid_method

class User(db.Model):
    __tablename__ = 'users'
    __table_args__ = {"schema": "a11y"}

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    profile = db.relationship('Profile', backref='user', lazy=True, uselist=False)

    @hybrid_method
    def get_id(self):
        return self.id

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'is_admin': self.profile.is_admin if self.profile else False,
            'is_active': self.is_active,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


    def __init__(self, email, password):
        self.email = email
        self.password = password

    def __repr__(self):
        return f'<User {self.email}>'


class Profile(db.Model):
    __tablename__ = 'profiles'
    __table_args__ = {"schema": "a11y"}

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('a11y.users.id'), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())


    def __init__(self, user, is_admin=False):
        self.user = user
        self.is_admin = is_admin

    def __repr__(self):
        return f'<Profile {self.user_id}>'
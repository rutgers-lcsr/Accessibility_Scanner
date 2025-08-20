
from models import db

class Website(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    base_url = db.Column(db.String(200), nullable=False)
    last_scanned = db.Column(db.DateTime, nullable=True)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    def __init__(self, base_url, last_scanned, active):
        self.base_url = base_url
        self.last_scanned = last_scanned
        self.active = active

    def __repr__(self):
        return f'<Website {self.base_url}>'

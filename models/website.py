
from urllib.parse import urlparse
from models import db
from sqlalchemy.ext.hybrid import hybrid_method

class Site(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(200), nullable=False)
    last_scanned = db.Column(db.DateTime, nullable=True)
    website_id = db.Column(db.Integer, db.ForeignKey('website.id'))
    reports = db.relationship('Report', back_populates='site', lazy='dynamic')
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    
    def __init__(self, url, website_id):
        parsed = urlparse(url)
        if not all([parsed.scheme, parsed.netloc]):
            raise ValueError("Invalid URL")
        
        self.url = url
        self.website_id = website_id

class Website(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    base_url = db.Column(db.String(200), nullable=False)
    domain_id = db.Column(db.Integer, db.ForeignKey('domains.id'))
    domain = db.relationship('Domains', backref='websites', lazy=True)
    sites = db.relationship('Site', backref='website', lazy='dynamic')
    last_scanned = db.Column(db.DateTime, nullable=True)
    active = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    def __init__(self, url):
        base_url = urlparse(url).netloc
        self.base_url = base_url

    def __repr__(self):
        return f'<Website {self.base_url}>'


# Domains can only be created by the admins
class Domains(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    domain = db.Column(db.String(200), nullable=False)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    
    @hybrid_method
    def part_of_domain(self, url):
        parsed = urlparse(url)

        if not parsed.netloc:
            return False

        return parsed.netloc.endswith(self.domain)

    def to_dict(self):
        return {
            'id': self.id,
            'domain': self.domain,
            'active': self.active,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

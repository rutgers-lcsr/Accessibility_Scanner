"""Site health: whether a website's home page is up, its TLS certificate, security
headers, platform, and the content it is required to carry.

services.health checks every website that is not retired on a schedule. Each check
appends a HealthCheck row (the uptime history) and overwrites the website's
WebsiteHealth row (the latest picture). Content requirements are defined by site
admins and apply only to the websites they are assigned to.
"""
from datetime import datetime
from typing import List

from sqlalchemy import Index
from sqlalchemy.orm import Mapped

from models import db

# Response headers a website is expected to send; see services.health.SECURITY_HEADERS.
REQUIREMENT_CHECK_TYPES = ('link_text', 'link_href', 'selector', 'text')

WebsiteRequirementAssoc = db.Table(
    'website_requirement',
    db.Column('website_id', db.Integer, db.ForeignKey('website.id', ondelete='CASCADE'), primary_key=True),
    db.Column('requirement_id', db.Integer, db.ForeignKey('content_requirement.id', ondelete='CASCADE'), primary_key=True),
)


def _iso(value):
    return value.strftime("%Y-%m-%dT%H:%M:%SZ") if value else None


class HealthCheck(db.Model):
    """One probe of a website's home page."""
    __tablename__ = 'health_check'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    website_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('website.id', ondelete='CASCADE'), nullable=False)
    checked_at: Mapped[datetime] = db.Column(db.DateTime, nullable=False)
    up: Mapped[bool] = db.Column(db.Boolean, nullable=False)
    status_code: Mapped[int] = db.Column(db.Integer, nullable=True)
    response_ms: Mapped[int] = db.Column(db.Integer, nullable=True)
    error: Mapped[str] = db.Column(db.String(500), nullable=True)

    __table_args__ = (Index('ix_health_check_website_time', 'website_id', 'checked_at'),)

    def to_dict(self) -> dict:
        return {
            'checked_at': _iso(self.checked_at),
            'up': self.up,
            'status_code': self.status_code,
            'response_ms': self.response_ms,
            'error': self.error,
        }


class WebsiteHealth(db.Model):
    """The latest health check of a website (one row per website)."""
    __tablename__ = 'website_health'

    website_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('website.id', ondelete='CASCADE'), primary_key=True)
    checked_at: Mapped[datetime] = db.Column(db.DateTime, nullable=False)
    up: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=False)
    status_code: Mapped[int] = db.Column(db.Integer, nullable=True)
    response_ms: Mapped[int] = db.Column(db.Integer, nullable=True)
    error: Mapped[str] = db.Column(db.String(500), nullable=True)
    final_url: Mapped[str] = db.Column(db.String(1000), nullable=True)
    # When the state last flipped between up and down (for "down since").
    up_changed_at: Mapped[datetime] = db.Column(db.DateTime, nullable=True)
    # http:// on the same host answers with a redirect to https://.
    https_redirect: Mapped[bool] = db.Column(db.Boolean, nullable=True)
    tls_valid: Mapped[bool] = db.Column(db.Boolean, nullable=True)
    tls_expires_at: Mapped[datetime] = db.Column(db.DateTime, nullable=True)
    tls_issuer: Mapped[str] = db.Column(db.String(300), nullable=True)
    tls_error: Mapped[str] = db.Column(db.String(500), nullable=True)
    # {header name: value or None}
    security_headers: Mapped[dict] = db.Column(db.JSON, nullable=True)
    platform: Mapped[str] = db.Column(db.String(100), nullable=True)
    platform_version: Mapped[str] = db.Column(db.String(100), nullable=True)
    server: Mapped[str] = db.Column(db.String(200), nullable=True)
    # [{'id', 'name', 'passed', 'detail'}] for the website's content requirements.
    requirements: Mapped[list] = db.Column(db.JSON, nullable=True)

    website = db.relationship('Website', backref=db.backref('health', uselist=False, passive_deletes=True))

    def to_dict(self) -> dict:
        return {
            'checked_at': _iso(self.checked_at),
            'up': self.up,
            'up_changed_at': _iso(self.up_changed_at),
            'status_code': self.status_code,
            'response_ms': self.response_ms,
            'error': self.error,
            'final_url': self.final_url,
            'https_redirect': self.https_redirect,
            'tls_valid': self.tls_valid,
            'tls_expires_at': _iso(self.tls_expires_at),
            'tls_issuer': self.tls_issuer,
            'tls_error': self.tls_error,
            'security_headers': self.security_headers or {},
            'platform': self.platform,
            'platform_version': self.platform_version,
            'server': self.server,
            'requirements': self.requirements or [],
        }


class ContentRequirement(db.Model):
    """Something a website's home page must carry, such as a link to the accessibility
    statement. ``pattern`` is a case-insensitive regular expression matched against
    link text, link targets or the page text, or a CSS selector that must match."""
    __tablename__ = 'content_requirement'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    name: Mapped[str] = db.Column(db.String(200), nullable=False)
    description: Mapped[str] = db.Column(db.Text, nullable=True)
    check_type: Mapped[str] = db.Column(db.String(20), nullable=False)
    pattern: Mapped[str] = db.Column(db.String(500), nullable=False)
    enabled: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at: Mapped[datetime] = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    websites: Mapped[List['Website']] = db.relationship('Website', secondary=WebsiteRequirementAssoc,
                                                        backref=db.backref('requirements', lazy='select'), lazy='select')

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'check_type': self.check_type,
            'pattern': self.pattern,
            'enabled': self.enabled,
            'website_ids': [website.id for website in self.websites],
        }

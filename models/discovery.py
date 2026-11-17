"""Hosts found under an allow-listed domain that may be websites nobody has added yet.

Discovery runs only for a domain a site admin picks (services.discovery): from
certificate transparency logs and the links and resources the crawled websites point
at. Each host is probed once in a while for DNS, an HTTP answer and a page title, so
the list shows which ones are live websites.
"""
from datetime import datetime

from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped

from models import db

DISCOVERED_STATUSES = ('new', 'ignored')


def _iso(value):
    return value.strftime("%Y-%m-%dT%H:%M:%SZ") if value else None


class DiscoveredHost(db.Model):
    __tablename__ = 'discovered_host'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    domain_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('domains.id', ondelete='CASCADE'), nullable=False, index=True)
    host: Mapped[str] = db.Column(db.String(255), nullable=False)
    # Comma-separated subset of ct (certificate transparency) and links (crawled pages).
    sources: Mapped[str] = db.Column(db.String(50), nullable=False, default='')
    status: Mapped[str] = db.Column(db.String(10), nullable=False, default='new')
    note: Mapped[str] = db.Column(db.Text, nullable=True)
    first_seen: Mapped[datetime] = db.Column(db.DateTime, nullable=False)
    last_seen: Mapped[datetime] = db.Column(db.DateTime, nullable=False)
    # Probe results.
    resolves: Mapped[bool] = db.Column(db.Boolean, nullable=True)
    http_status: Mapped[int] = db.Column(db.Integer, nullable=True)
    final_url: Mapped[str] = db.Column(db.String(1000), nullable=True)
    title: Mapped[str] = db.Column(db.String(300), nullable=True)
    probe_error: Mapped[str] = db.Column(db.String(500), nullable=True)
    checked_at: Mapped[datetime] = db.Column(db.DateTime, nullable=True)

    __table_args__ = (UniqueConstraint('domain_id', 'host', name='uq_discovered_domain_host'),)

    def to_dict(self, tracked_website_id: int | None = None) -> dict:
        return {
            'id': self.id,
            'domain_id': self.domain_id,
            'host': self.host,
            'sources': [s for s in (self.sources or '').split(',') if s],
            'status': 'tracked' if tracked_website_id else self.status,
            'website_id': tracked_website_id,
            'note': self.note,
            'first_seen': _iso(self.first_seen),
            'last_seen': _iso(self.last_seen),
            'resolves': self.resolves,
            'http_status': self.http_status,
            'final_url': self.final_url,
            'title': self.title,
            'probe_error': self.probe_error,
            'checked_at': _iso(self.checked_at),
        }

"""Links found on a website's pages (any host) and whether their targets respond.

The crawler records every http(s) link with the page it is on and its link text; after
the crawl services.links probes each target. Statuses: pending (not yet checked), ok,
broken (4xx), blocked (login or bot protection: 401, 403, 429, 999; not reported as
broken), error (5xx, timeout, DNS or connection failure, too many redirects), skipped
(robots.txt or a non-public host).
"""
from datetime import datetime
from typing import List

from sqlalchemy import Index, UniqueConstraint
from sqlalchemy.orm import Mapped

from models import db

LINK_STATUSES = ('pending', 'ok', 'broken', 'blocked', 'error', 'skipped')
# Listing order: what needs attention first.
LINK_STATUS_ORDER = ('broken', 'error', 'blocked', 'pending', 'skipped', 'ok')


class LinkSource(db.Model):
    """A page that links to a target, with the text of that link."""
    __tablename__ = 'link_source'

    link_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('link.id', ondelete='CASCADE'), primary_key=True)
    site_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('site.id', ondelete='CASCADE'), primary_key=True)
    text: Mapped[str] = db.Column(db.String(300), nullable=True)

    link = db.relationship('Link', back_populates='sources')
    site = db.relationship('Site')


class Link(db.Model):
    __tablename__ = 'link'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    website_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('website.id', ondelete='CASCADE'), nullable=False, index=True)
    url: Mapped[str] = db.Column(db.String(1000), nullable=False)
    external: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=False)
    status: Mapped[str] = db.Column(db.String(16), nullable=False, default='pending')
    status_code: Mapped[int] = db.Column(db.Integer, nullable=True)
    final_url: Mapped[str] = db.Column(db.String(1000), nullable=True)
    error: Mapped[str] = db.Column(db.Text, nullable=True)
    first_seen: Mapped[datetime] = db.Column(db.DateTime, nullable=False)
    last_seen: Mapped[datetime] = db.Column(db.DateTime, nullable=False)
    checked_at: Mapped[datetime] = db.Column(db.DateTime, nullable=True)
    created_at: Mapped[datetime] = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at: Mapped[datetime] = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    __table_args__ = (
        UniqueConstraint('website_id', 'url', name='uq_link_website_url'),
        Index('ix_link_website_status', 'website_id', 'status'),
    )

    website = db.relationship('Website', back_populates='links_found')
    # The pages that link to it; small lists, loaded with the link.
    sources: Mapped[List['LinkSource']] = db.relationship('LinkSource', back_populates='link', lazy='select',
                                                          cascade='all, delete-orphan')

    def to_dict(self, report_ids: dict | None = None) -> dict:
        """``report_ids`` maps site id to that page's latest report id, so the UI can link
        each source page to its report (services.links.latest_report_ids)."""
        iso = lambda value: value.strftime("%Y-%m-%dT%H:%M:%SZ") if value else None
        report_ids = report_ids or {}
        found_on = sorted(({'url': source.site.url, 'text': source.text, 'site_id': source.site_id,
                            'report_id': report_ids.get(source.site_id)} for source in self.sources), key=lambda s: s['url'])
        return {
            'id': self.id,
            'website_id': self.website_id,
            'url': self.url,
            'external': self.external,
            'status': self.status,
            'status_code': self.status_code,
            'final_url': self.final_url,
            'error': self.error,
            'first_seen': iso(self.first_seen),
            'last_seen': iso(self.last_seen),
            'checked_at': iso(self.checked_at),
            'found_on': found_on,
            'found_on_count': len(found_on),
        }

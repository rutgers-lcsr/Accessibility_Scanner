"""Documents linked from a website's pages (PDF, Word, PowerPoint, Excel).

The crawler never opens them as pages; it records the links and, for PDFs on the
website's own host, downloads and inspects them (services.documents): tagged or not,
title, language, page count. Statuses: pending (PDF not yet checked), tagged,
untagged, unreachable, too_large, unreadable, skipped (robots.txt or the per-scan cap),
not_checked (not a PDF, or hosted elsewhere).
"""
from datetime import datetime
from typing import List

from sqlalchemy import Index, UniqueConstraint
from sqlalchemy.orm import Mapped

from models import db

DOCUMENT_STATUSES = ('pending', 'tagged', 'untagged', 'unreachable', 'too_large', 'unreadable', 'skipped', 'not_checked')
# Listing order: what needs attention first.
DOCUMENT_STATUS_ORDER = ('untagged', 'pending', 'unreachable', 'too_large', 'unreadable', 'tagged', 'skipped', 'not_checked')

DocumentSiteAssoc = db.Table(
    'document_site_assoc',
    db.Column('document_id', db.Integer, db.ForeignKey('document.id', ondelete='CASCADE'), primary_key=True),
    db.Column('site_id', db.Integer, db.ForeignKey('site.id', ondelete='CASCADE'), primary_key=True),
)


class Document(db.Model):
    __tablename__ = 'document'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    website_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('website.id', ondelete='CASCADE'), nullable=False, index=True)
    url: Mapped[str] = db.Column(db.String(1000), nullable=False)
    doc_type: Mapped[str] = db.Column(db.String(8), nullable=False)
    status: Mapped[str] = db.Column(db.String(16), nullable=False, default='pending')
    first_seen: Mapped[datetime] = db.Column(db.DateTime, nullable=False)
    last_seen: Mapped[datetime] = db.Column(db.DateTime, nullable=False)
    checked_at: Mapped[datetime] = db.Column(db.DateTime, nullable=True)
    size_bytes: Mapped[int] = db.Column(db.Integer, nullable=True)
    page_count: Mapped[int] = db.Column(db.Integer, nullable=True)
    title: Mapped[str] = db.Column(db.String(500), nullable=True)
    has_title: Mapped[bool] = db.Column(db.Boolean, nullable=True)
    language: Mapped[str] = db.Column(db.String(32), nullable=True)
    error: Mapped[str] = db.Column(db.Text, nullable=True)
    created_at: Mapped[datetime] = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at: Mapped[datetime] = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    __table_args__ = (
        UniqueConstraint('website_id', 'url', name='uq_document_website_url'),
        Index('ix_document_website_status', 'website_id', 'status'),
    )

    website = db.relationship('Website', back_populates='documents')
    # The pages that link to it; small lists, loaded with the document.
    sites: Mapped[List['Site']] = db.relationship('Site', secondary=DocumentSiteAssoc, back_populates='documents', lazy='select')

    def to_dict(self) -> dict:
        iso = lambda value: value.strftime("%Y-%m-%dT%H:%M:%SZ") if value else None
        found_on = sorted(site.url for site in self.sites)
        return {
            'id': self.id,
            'website_id': self.website_id,
            'url': self.url,
            'type': self.doc_type,
            'status': self.status,
            'first_seen': iso(self.first_seen),
            'last_seen': iso(self.last_seen),
            'checked_at': iso(self.checked_at),
            'size_bytes': self.size_bytes,
            'page_count': self.page_count,
            'title': self.title,
            'has_title': self.has_title,
            'language': self.language,
            'error': self.error,
            'found_on': found_on,
            'found_on_count': len(found_on),
        }

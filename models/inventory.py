"""What a crawl finds on a website's pages besides accessibility results: media (with
whether it has captions) and third-party hosts, plus the vendor register those hosts
are matched against.

The crawler collects both per page (scanner.browser.parse) and services.inventory brings
the website's rows in line after the crawl, like documents and links.
"""
from datetime import date, datetime
from typing import List

from sqlalchemy import Index, UniqueConstraint
from sqlalchemy.orm import Mapped

from models import db

MEDIA_KINDS = ('video', 'audio', 'embed')
# What the crawl could tell: a <video> with a captions/subtitles <track> has captions; a
# <video> without one does not; audio and embedded players cannot be told from the page.
CAPTION_STATES = ('present', 'missing', 'unknown')
# What a person has confirmed, which wins over what the crawl found.
CAPTION_OVERRIDES = ('verified', 'missing')
VENDOR_STATUSES = ('approved', 'under_review', 'not_approved')
MAX_URL_LENGTH = 1000


def _iso(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%dT%H:%M:%SZ")
    return value.isoformat()


MediaSource = db.Table(
    'media_source',
    db.Column('media_id', db.Integer, db.ForeignKey('media_item.id', ondelete='CASCADE'), primary_key=True),
    db.Column('site_id', db.Integer, db.ForeignKey('site.id', ondelete='CASCADE'), primary_key=True),
)


class MediaItem(db.Model):
    """A video, audio file or embedded player found on a website's pages."""
    __tablename__ = 'media_item'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    website_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('website.id', ondelete='CASCADE'), nullable=False, index=True)
    url: Mapped[str] = db.Column(db.String(MAX_URL_LENGTH), nullable=False)
    kind: Mapped[str] = db.Column(db.String(10), nullable=False)
    provider: Mapped[str] = db.Column(db.String(50), nullable=True)
    captions: Mapped[str] = db.Column(db.String(10), nullable=False, default='unknown')
    audio_description: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=False)
    caption_override: Mapped[str] = db.Column(db.String(10), nullable=True)
    note: Mapped[str] = db.Column(db.Text, nullable=True)
    override_by: Mapped[int] = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    override_at: Mapped[datetime] = db.Column(db.DateTime, nullable=True)
    first_seen: Mapped[datetime] = db.Column(db.DateTime, nullable=False)
    last_seen: Mapped[datetime] = db.Column(db.DateTime, nullable=False)

    __table_args__ = (UniqueConstraint('website_id', 'url', name='uq_media_website_url'),)

    pages = db.relationship('Site', secondary=MediaSource, lazy='select')
    override_user = db.relationship('User', foreign_keys=[override_by], lazy=True)

    @property
    def caption_status(self) -> str:
        """What to show: a person's verdict, else what the crawl found."""
        if self.caption_override == 'verified':
            return 'present'
        if self.caption_override == 'missing':
            return 'missing'
        return self.captions

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'url': self.url,
            'kind': self.kind,
            'provider': self.provider,
            'captions': self.captions,
            'caption_override': self.caption_override,
            'caption_status': self.caption_status,
            'audio_description': self.audio_description,
            'note': self.note,
            'override_by': self.override_user.username if self.override_user else None,
            'override_at': _iso(self.override_at),
            'first_seen': _iso(self.first_seen),
            'last_seen': _iso(self.last_seen),
            'pages': sorted(site.url for site in self.pages),
        }


class ThirdPartyHost(db.Model):
    """A host other than the website's own that its pages load scripts, frames or
    stylesheets from, or send forms to."""
    __tablename__ = 'third_party_host'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    website_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('website.id', ondelete='CASCADE'), nullable=False)
    host: Mapped[str] = db.Column(db.String(255), nullable=False)
    # Comma-separated subset of script, iframe, stylesheet, form.
    kinds: Mapped[str] = db.Column(db.String(100), nullable=False, default='')
    example_url: Mapped[str] = db.Column(db.String(MAX_URL_LENGTH), nullable=True)
    page_count: Mapped[int] = db.Column(db.Integer, nullable=False, default=0)
    # A few of the pages that use it (JSON list of URLs).
    pages: Mapped[list] = db.Column(db.JSON, nullable=True)
    first_seen: Mapped[datetime] = db.Column(db.DateTime, nullable=False)
    last_seen: Mapped[datetime] = db.Column(db.DateTime, nullable=False)

    __table_args__ = (
        UniqueConstraint('website_id', 'host', name='uq_third_party_website_host'),
        Index('ix_third_party_host', 'host'),
    )

    def to_dict(self, vendor: 'Vendor | None' = None) -> dict:
        return {
            'id': self.id,
            'website_id': self.website_id,
            'host': self.host,
            'kinds': [k for k in (self.kinds or '').split(',') if k],
            'example_url': self.example_url,
            'page_count': self.page_count,
            'pages': self.pages or [],
            'first_seen': _iso(self.first_seen),
            'last_seen': _iso(self.last_seen),
            'vendor': vendor.summary() if vendor else None,
        }


class Vendor(db.Model):
    """A third party a website relies on, with its accessibility conformance report
    (VPAT/ACR) and when it is due for review. ``hosts`` are host names, one per line;
    a host matches when it is one of them or a subdomain of one."""
    __tablename__ = 'vendor'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    name: Mapped[str] = db.Column(db.String(200), nullable=False)
    hosts: Mapped[str] = db.Column(db.Text, nullable=False, default='')
    status: Mapped[str] = db.Column(db.String(20), nullable=False, default='under_review')
    vpat_url: Mapped[str] = db.Column(db.String(1000), nullable=True)
    vpat_date: Mapped[date] = db.Column(db.Date, nullable=True)
    review_due: Mapped[date] = db.Column(db.Date, nullable=True)
    contact: Mapped[str] = db.Column(db.String(300), nullable=True)
    notes: Mapped[str] = db.Column(db.Text, nullable=True)
    created_at: Mapped[datetime] = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at: Mapped[datetime] = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    def host_list(self) -> List[str]:
        return [h.strip().lower().lstrip('.') for h in (self.hosts or '').splitlines() if h.strip()]

    def matches(self, host: str) -> bool:
        host = host.lower()
        return any(host == name or host.endswith('.' + name) for name in self.host_list())

    def review_overdue(self, today: date | None = None) -> bool:
        return bool(self.review_due and self.review_due < (today or date.today()))

    def summary(self) -> dict:
        return {'id': self.id, 'name': self.name, 'status': self.status,
                'has_vpat': bool(self.vpat_url), 'review_overdue': self.review_overdue()}

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'hosts': self.host_list(),
            'status': self.status,
            'vpat_url': self.vpat_url,
            'vpat_date': _iso(self.vpat_date),
            'review_due': _iso(self.review_due),
            'review_overdue': self.review_overdue(),
            'contact': self.contact,
            'notes': self.notes,
        }


def match_vendor(host: str, vendors: List[Vendor]) -> Vendor | None:
    """The vendor with the most specific host entry matching ``host``."""
    best, best_length = None, -1
    for vendor in vendors:
        for name in vendor.host_list():
            if (host == name or host.endswith('.' + name)) and len(name) > best_length:
                best, best_length = vendor, len(name)
    return best

"""One failing element on one page, tracked across scans.

A finding is identified by its page and a fingerprint of the rule and the element's
selector (see services.findings). The scanner creates findings from every stored
report, marks the ones that vanished as fixed and reopens ones that come back; people
can mark a finding false positive or accepted, which suppresses it from the counts.
"""
from datetime import datetime

from sqlalchemy import Index, UniqueConstraint
from sqlalchemy.orm import Mapped

from models import db

FINDING_STATUSES = ('open', 'fixed', 'false_positive', 'accepted')
SUPPRESSED_STATUSES = ('false_positive', 'accepted')


class Finding(db.Model):
    __tablename__ = 'finding'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    site_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('site.id', ondelete='CASCADE'), nullable=False, index=True)
    rule_id: Mapped[str] = db.Column(db.String(100), nullable=False)
    fingerprint: Mapped[str] = db.Column(db.String(40), nullable=False)
    impact: Mapped[str] = db.Column(db.String(20), nullable=True)
    # Denormalised from the report: the Rule table only holds custom rules.
    help: Mapped[str] = db.Column(db.String(500), nullable=True)
    help_url: Mapped[str] = db.Column(db.String(500), nullable=True)
    selector: Mapped[str] = db.Column(db.Text, nullable=True)
    html: Mapped[str] = db.Column(db.Text, nullable=True)
    first_seen: Mapped[datetime] = db.Column(db.DateTime, nullable=False)
    last_seen: Mapped[datetime] = db.Column(db.DateTime, nullable=False)
    # The report it was last seen in; a finding is "current" when this is the page's
    # latest report.
    last_report_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('report.id', ondelete='SET NULL'), nullable=True)
    status: Mapped[str] = db.Column(db.String(20), nullable=False, default='open')
    # Who set the status; NULL means the scanner did (auto-closed or reopened).
    status_by: Mapped[int] = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    status_at: Mapped[datetime] = db.Column(db.DateTime, nullable=True)
    note: Mapped[str] = db.Column(db.Text, nullable=True)
    created_at: Mapped[datetime] = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at: Mapped[datetime] = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    __table_args__ = (
        UniqueConstraint('site_id', 'fingerprint', name='uq_finding_site_fingerprint'),
        Index('ix_finding_site_status', 'site_id', 'status'),
    )

    site = db.relationship('Site', back_populates='findings')
    status_user = db.relationship('User', foreign_keys=[status_by], lazy=True)

    @property
    def suppressed(self) -> bool:
        return self.status in SUPPRESSED_STATUSES

    def to_dict(self) -> dict:
        iso = lambda value: value.strftime("%Y-%m-%dT%H:%M:%SZ") if value else None
        return {
            'id': self.id,
            'site_id': self.site_id,
            'rule_id': self.rule_id,
            'fingerprint': self.fingerprint,
            'impact': self.impact,
            'help': self.help,
            'help_url': self.help_url,
            'selector': self.selector,
            'html': self.html,
            'first_seen': iso(self.first_seen),
            'last_seen': iso(self.last_seen),
            'last_report_id': self.last_report_id,
            'status': self.status,
            'status_by': self.status_user.username if self.status_user else None,
            'status_at': iso(self.status_at),
            'note': self.note,
        }

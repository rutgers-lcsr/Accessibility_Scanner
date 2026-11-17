"""Compliance records: the exceptions register and manual reviews.

An exception documents why some findings on a website will not be fixed by their
deadline (archived content, third-party content, undue burden, ...). Website editors
request one; a site admin approves or rejects it, normally with an expiry date. While
approved and not expired it exempts the findings it covers from deadlines
(services.compliance); it never hides them from the counts.

A manual review records a person's (or an agent's) pass through the checks automated
scanning cannot do, item by item (services.reviews.CHECKLIST).
"""
from datetime import date, datetime

from sqlalchemy.orm import Mapped

from models import db

EXCEPTION_KINDS = ('archived', 'third_party', 'undue_burden', 'fundamental_alteration', 'other')
EXCEPTION_STATUSES = ('requested', 'approved', 'rejected')
REVIEW_RESULTS = ('pass', 'fail', 'not_applicable', 'not_tested')
REVIEW_STATUSES = ('in_progress', 'completed')
REVIEW_SOURCES = ('person', 'agent')


def _iso(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%dT%H:%M:%SZ")
    return value.isoformat()


class ComplianceException(db.Model):
    __tablename__ = 'compliance_exception'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    website_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('website.id', ondelete='CASCADE'), nullable=False, index=True)
    # What it covers: one rule (None = every rule) on pages starting with url_prefix
    # (None = every page).
    rule_id: Mapped[str] = db.Column(db.String(100), nullable=True)
    url_prefix: Mapped[str] = db.Column(db.String(500), nullable=True)
    kind: Mapped[str] = db.Column(db.String(30), nullable=False)
    reason: Mapped[str] = db.Column(db.Text, nullable=False)
    status: Mapped[str] = db.Column(db.String(20), nullable=False, default='requested')
    requested_by: Mapped[int] = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    requested_at: Mapped[datetime] = db.Column(db.DateTime, nullable=False)
    decided_by: Mapped[int] = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    decided_at: Mapped[datetime] = db.Column(db.DateTime, nullable=True)
    decision_note: Mapped[str] = db.Column(db.Text, nullable=True)
    expires_on: Mapped[date] = db.Column(db.Date, nullable=True)

    website = db.relationship('Website')
    requester = db.relationship('User', foreign_keys=[requested_by], lazy=True)
    decider = db.relationship('User', foreign_keys=[decided_by], lazy=True)

    def is_active(self, today: date | None = None) -> bool:
        today = today or date.today()
        return self.status == 'approved' and (self.expires_on is None or self.expires_on >= today)

    def display_status(self, today: date | None = None) -> str:
        """requested, approved, rejected or expired."""
        if self.status == 'approved' and not self.is_active(today):
            return 'expired'
        return self.status

    def covers(self, rule_id: str, url: str) -> bool:
        return (self.rule_id is None or self.rule_id == rule_id) and (
            self.url_prefix is None or (url or '').startswith(self.url_prefix))

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'website_id': self.website_id,
            'website_url': self.website.url if self.website else None,
            'rule_id': self.rule_id,
            'url_prefix': self.url_prefix,
            'kind': self.kind,
            'reason': self.reason,
            'status': self.display_status(),
            'requested_by': self.requester.username if self.requester else None,
            'requested_at': _iso(self.requested_at),
            'decided_by': self.decider.username if self.decider else None,
            'decided_at': _iso(self.decided_at),
            'decision_note': self.decision_note,
            'expires_on': _iso(self.expires_on),
        }


class ManualReview(db.Model):
    __tablename__ = 'manual_review'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    website_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('website.id', ondelete='CASCADE'), nullable=False, index=True)
    reviewer_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    source: Mapped[str] = db.Column(db.String(10), nullable=False, default='person')
    # Free text naming the tool or agent, for source 'agent'.
    tool: Mapped[str] = db.Column(db.String(200), nullable=True)
    status: Mapped[str] = db.Column(db.String(20), nullable=False, default='in_progress')
    pages: Mapped[list] = db.Column(db.JSON, nullable=True)
    # {checklist key: {'result': one of REVIEW_RESULTS, 'notes': str, 'pages': [urls]}}
    results: Mapped[dict] = db.Column(db.JSON, nullable=True)
    summary: Mapped[str] = db.Column(db.Text, nullable=True)
    started_at: Mapped[datetime] = db.Column(db.DateTime, nullable=False)
    completed_at: Mapped[datetime] = db.Column(db.DateTime, nullable=True)

    reviewer = db.relationship('User', lazy=True)

    def counts(self) -> dict:
        out = {key: 0 for key in REVIEW_RESULTS}
        for entry in (self.results or {}).values():
            result = (entry or {}).get('result')
            if result in out:
                out[result] += 1
        return out

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'website_id': self.website_id,
            'reviewer': self.reviewer.username if self.reviewer else None,
            'source': self.source,
            'tool': self.tool,
            'status': self.status,
            'pages': self.pages or [],
            'results': self.results or {},
            'counts': self.counts(),
            'summary': self.summary,
            'started_at': _iso(self.started_at),
            'completed_at': _iso(self.completed_at),
        }

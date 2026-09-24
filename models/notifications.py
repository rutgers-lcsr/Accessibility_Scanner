"""Per-user notification state: opt-outs from a website's emails, and when a website's
own people last opened its page.

A website's admin and users are its recipients; a row here removes one of them without
touching the website-wide switch (Website.should_email), which only site admins set.
"""
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy.orm import Mapped

from models import db


class NotificationOptOut(db.Model):
    __tablename__ = 'notification_opt_out'

    user_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    website_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('website.id', ondelete='CASCADE'), primary_key=True)
    created_at: Mapped[datetime] = db.Column(db.DateTime, default=db.func.current_timestamp())


class WebsiteView(db.Model):
    """When a website's admin or a member last opened its page. Engagement, not activity:
    the owner digests word themselves by it, but it never counts as fixing anything."""
    __tablename__ = 'website_view'

    user_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    website_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('website.id', ondelete='CASCADE'), primary_key=True)
    last_viewed_at: Mapped[datetime] = db.Column(db.DateTime, nullable=False)

    @staticmethod
    def touch(user_id: int, website_id: int, now: datetime | None = None) -> None:
        now = now or datetime.now(timezone.utc).replace(tzinfo=None)
        row = db.session.get(WebsiteView, (user_id, website_id))
        if row is None:
            db.session.add(WebsiteView(user_id=user_id, website_id=website_id, last_viewed_at=now))
        else:
            row.last_viewed_at = now
        db.session.commit()

    @staticmethod
    def by_website(website_ids) -> dict:
        """``{website_id: {user_id: last_viewed_at}}``."""
        result = defaultdict(dict)
        if not website_ids:
            return result
        rows = db.session.query(WebsiteView).filter(WebsiteView.website_id.in_(list(website_ids))).all()
        for row in rows:
            result[row.website_id][row.user_id] = row.last_viewed_at
        return result

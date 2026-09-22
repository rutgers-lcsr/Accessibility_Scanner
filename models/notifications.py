"""Per-user opt-out from a website's notification emails.

A website's admin and users are its recipients; a row here removes one of them without
touching the website-wide switch (Website.should_email), which only site admins set.
"""
from datetime import datetime

from sqlalchemy.orm import Mapped

from models import db


class NotificationOptOut(db.Model):
    __tablename__ = 'notification_opt_out'

    user_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    website_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('website.id', ondelete='CASCADE'), primary_key=True)
    created_at: Mapped[datetime] = db.Column(db.DateTime, default=db.func.current_timestamp())

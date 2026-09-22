"""An ad hoc audit of one page that is not registered as a website.

Only the request is stored: who asked, which URL, and the Celery task id. The result
lives in the Celery result backend for QUICK_SCAN_RESULT_TTL (services.quick_scan) and
the row is pruned on the same horizon.
"""
from datetime import datetime

from sqlalchemy.orm import Mapped

from models import db
from models.user import User


class QuickScan(db.Model):
    __tablename__ = 'quick_scans'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    task_id: Mapped[str] = db.Column(db.String(36), nullable=False, unique=True, index=True)
    url: Mapped[str] = db.Column(db.String(500), nullable=False)
    user_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at: Mapped[datetime] = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())

    user = db.relationship('User', lazy=True)

    def can_view(self, user: User) -> bool:
        if not user:
            return False
        if user.profile and user.profile.is_admin:
            return True
        return self.user_id == user.id

    @classmethod
    def prune(cls, older_than: datetime) -> int:
        """Delete request rows whose result has expired. Returns how many went."""
        deleted = db.session.query(cls).filter(cls.created_at < older_than).delete(synchronize_session=False)
        return deleted

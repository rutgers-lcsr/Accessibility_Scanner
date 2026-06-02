import hashlib
import secrets
from datetime import datetime, timezone

from sqlalchemy.orm import Mapped

from models import db
from models.user import User

TOKEN_PREFIX = "a11y_"


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class ApiKey(db.Model):
    __tablename__ = 'api_keys'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    user_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user: Mapped[User] = db.relationship('User', back_populates='api_keys')
    name: Mapped[str] = db.Column(db.String(255), nullable=False)
    # First few chars of the token, shown in the UI so users can identify a key
    prefix: Mapped[str] = db.Column(db.String(16), nullable=False)
    # sha256 hex digest of the full token; the plaintext is never stored
    key_hash: Mapped[str] = db.Column(db.String(64), unique=True, nullable=False)
    last_used_at: Mapped[datetime | None] = db.Column(db.DateTime, nullable=True)
    revoked: Mapped[bool] = db.Column(db.Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = db.Column(db.DateTime, default=db.func.current_timestamp())

    def __repr__(self):
        return f"<ApiKey {self.id} {self.prefix}... user={self.user_id}>"

    @classmethod
    def create(cls, user: User, name: str) -> tuple['ApiKey', str]:
        """Create a new key for the user. Returns (api_key, plaintext_token).

        The plaintext token is only available here; only its hash is persisted.
        """
        token = TOKEN_PREFIX + secrets.token_urlsafe(32)
        api_key = cls(
            user_id=user.id,
            name=name,
            prefix=token[:12],
            key_hash=_hash_token(token),
            revoked=False,
        )
        db.session.add(api_key)
        db.session.commit()
        return api_key, token

    @classmethod
    def verify(cls, token: str) -> 'ApiKey | None':
        """Resolve a non-revoked ApiKey from a plaintext token, or None."""
        if not token:
            return None
        return db.session.query(cls).filter_by(
            key_hash=_hash_token(token), revoked=False
        ).first()

    def touch(self):
        """Record that the key was just used."""
        self.last_used_at = datetime.now(timezone.utc)
        db.session.commit()

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'prefix': self.prefix,
            'last_used_at': self.last_used_at.strftime("%Y-%m-%dT%H:%M:%SZ") if self.last_used_at else None,
            'created_at': self.created_at.strftime("%Y-%m-%dT%H:%M:%SZ") if self.created_at else None,
        }

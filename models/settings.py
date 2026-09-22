
from typing import Literal
from models import db
from sqlalchemy.orm import Mapped
from datetime import datetime
from typing import Literal, get_args


AppSetting = Literal[
    "default_tags",
    "default_rate_limit",
    "default_should_auto_scan",
    "default_should_auto_activate",
    "default_notify_on_completion",
    "default_email_domain",
    "scan_page_concurrency",
    "max_pages",
    "max_depth",
    "crawl_delay_ms",
    "admin_digest_enabled",
    "retention_enabled",
    "retention_keep_days",
    "retention_max_days",
]
APP_SETTINGS: list[AppSetting] = list(get_args(AppSetting))

# The value every setting has until an admin changes it. Settings.get falls back to
# this, so callers never need to repeat a default (and cannot disagree with it).
DEFAULTS: dict[AppSetting, str] = {
    "default_tags": 'wcag2a, wcag2aa, wcag21a, wcag21aa',
    "default_rate_limit": "30",
    "default_should_auto_scan": "true",
    "default_should_auto_activate": "false",
    "default_notify_on_completion": "true",
    "default_email_domain": "",
    "scan_page_concurrency": "3",
    "max_pages": "500",
    "max_depth": "5",
    "crawl_delay_ms": "250",
    "admin_digest_enabled": "true",
    # Report retention is opt-in: run `flask maintenance retention --dry-run` first.
    "retention_enabled": "false",
    "retention_keep_days": "90",
    "retention_max_days": "365",
}

class Settings(db.Model):
    __tablename__ = 'settings'
    
    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    key: Mapped[str] = db.Column(db.String(255), nullable=False, unique=True)
    value: Mapped[str] = db.Column(db.Text, nullable=False)
    description: Mapped[str] = db.Column(db.Text, nullable=True)
    created_at: Mapped[datetime] = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at: Mapped[datetime] = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    
    def __repr__(self):
        return f"<Settings {self.key}={self.value}>"
    
    @staticmethod
    def get(key: AppSetting, default: str = None) -> str | None:
        """The stored value, else ``default``, else the declared default for the key."""
        setting = db.session.query(Settings).filter_by(key=key).first()
        if setting:
            return setting.value
        if default is not None:
            return default
        return DEFAULTS.get(key)
    
    @staticmethod
    def set(key: AppSetting, value: str, description: str = None) -> None:
        setting = db.session.query(Settings).filter_by(key=key).first()
        if setting:
            setting.value = value
            if description:
                setting.description = description
        else:
            setting = Settings(key=key, value=value, description=description)
            db.session.add(setting)
        db.session.commit()

    @staticmethod
    def to_dict() -> dict:
        settings = db.session.query(Settings).all()
        return {setting.key: setting.value for setting in settings}
    
    @staticmethod
    def init_defaults() -> None:
        for key, value in DEFAULTS.items():
            if not db.session.query(Settings).filter_by(key=key).first():
                setting = Settings(key=key, value=value)
                db.session.add(setting)
        db.session.commit()
    
    
    

from typing import Literal
from models import db
from sqlalchemy.orm import Mapped
from datetime import datetime


app_setting = Literal['default_tags', 'default_rate_limit', 'default_should_auto_scan', 'default_notify_on_completion', 'default_email_domain']


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
    def get(key: app_setting, default: str = None) -> str | None:
        setting = db.session.query(Settings).filter_by(key=key).first()
        if setting:
            return setting.value
        return default
    
    @staticmethod
    def set(key: app_setting, value: str, description: str = None) -> None:
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
        defaults = {
            "default_tags": 'wcag2a, wcag2aa, wcag21a, wcag21aa',
            "default_rate_limit": "30",
            "default_should_auto_scan": "true",
            "default_notify_on_completion": "true",
            "default_email_domain": "",
        }
        for key, value in defaults.items():
            if not db.session.query(Settings).filter_by(key=key).first():
                setting = Settings(key=key, value=value)
                db.session.add(setting)
        db.session.commit()
    
    
    
"""Shared fixtures for the API test suite.

A throwaway sqlite database is used. The DATABASE_URL env var is set *before*
importing the app so config.py and models/__init__.py pick the sqlite (schema-less)
path, then the schema is rebuilt fresh for every test for isolation.
"""
import os
import tempfile
from datetime import datetime, timedelta, timezone

import pytest

# Must be set before importing app/config/models.
_DB_FILE = os.path.join(tempfile.gettempdir(), "a11y_test.db")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_DB_FILE}")
os.environ.setdefault("TESTING", "True")


@pytest.fixture()
def app():
    from app import create_app
    from models import db
    from models.settings import Settings

    application = create_app()
    application.config["TESTING"] = True

    with application.app_context():
        db.drop_all()
        db.create_all()
        Settings.init_defaults()
        try:
            yield application
        finally:
            db.session.remove()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def make_user(app):
    from models import db
    from models.user import Profile, User

    def _make(username="alice", is_admin=False):
        user = User(username=username, email=f"{username}@rutgers.edu")
        user.profile = Profile(user=user, is_admin=is_admin)
        db.session.add(user)
        db.session.commit()
        return user

    return _make


@pytest.fixture()
def make_website(app):
    """Create a Website (with its owning Domain) owned by ``owner``."""
    from models import db
    from models.website import Domain, Website

    def _make(owner, base="https://example.com", public=False):
        netloc = base.split("//", 1)[1]
        domain = db.session.query(Domain).filter_by(domain=netloc).first()
        if not domain:
            domain = Domain(domain=netloc)
            db.session.add(domain)
            db.session.commit()
        website = Website(url=base, user_id=owner.id)
        website.public = public
        db.session.add(website)
        db.session.commit()
        return website

    return _make


@pytest.fixture()
def add_site(app):
    """Attach a Site (page) to an existing Website."""
    from models import db
    from models.website import Site

    def _make(website, page="/page"):
        site = Site(url=website.url + page, website=website)
        db.session.add(site)
        db.session.commit()
        return site

    return _make


@pytest.fixture()
def make_site(make_website, add_site):
    """Create a Site (with its owning Domain + Website) owned by ``owner``."""

    def _make(owner, base="https://example.com", page="/page", public=False):
        website = make_website(owner, base=base, public=public)
        return add_site(website, page=page)

    return _make


@pytest.fixture()
def add_report(app):
    """Attach a report to a site. ``when`` controls the timestamp for 'latest' tests."""
    from models import db
    from models.report import Report

    def _make(site, url=None, when=None, violations=None):
        if when is None:
            when = datetime.now(timezone.utc)
        if violations is None:
            violations = [
                {
                    "id": "color-contrast",
                    "impact": "serious",
                    "description": "Elements must meet contrast ratio thresholds",
                    "help": "Ensure contrast",
                    "helpUrl": "https://example.com/rules/color-contrast",
                    "nodes": [
                        {
                            "target": ["div.banner"],
                            "html": "<div class='banner'>hi</div>",
                            "failureSummary": "Fix the contrast",
                        }
                    ],
                }
            ]
        data = {
            "url": url or site.url,
            "base_url": "https://example.com",
            "timestamp": when.isoformat(),
            "report": {
                "violations": violations,
                "incomplete": [],
                "inaccessible": [],
                "passes": [],
            },
            "links": [],
            "videos": [],
            "imgs": [],
            "tabable": True,
            "photo": None,
            "tags": ["wcag2a"],
        }
        report = Report(data, site.id)
        db.session.add(report)
        db.session.commit()
        return report

    return _make


@pytest.fixture()
def make_api_key(app):
    from models.api_key import ApiKey

    def _make(user, name="test key"):
        api_key, token = ApiKey.create(user, name)
        return api_key, token

    return _make


@pytest.fixture()
def jwt_header(app):
    """Build an Authorization header carrying a JWT for the given user."""
    from flask_jwt_extended import create_access_token

    def _make(user):
        token = create_access_token(identity=user, expires_delta=timedelta(hours=1))
        return {"Authorization": f"Bearer {token}"}

    return _make

"""A finished crawl writes the website's status before it returns, and sends no mail:
the website's people hear about it in their next owner digest."""
import asyncio
import types
from datetime import datetime, timezone

import pytest

import mail.emails as emails_mod
import models.website as website_models
import scanner.scan as scan_mod
from models import db


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setattr(website_models, "is_valid_url", lambda url: True)


def _rule(rule_id, impact="serious", nodes=(("#a", "<p>a</p>"),)):
    return {"id": rule_id, "impact": impact, "help": f"Fix {rule_id}", "helpUrl": "https://x",
            "nodes": [{"target": [s], "html": h} for s, h in nodes]}


class _FakePlaywright:
    async def __aenter__(self):
        async def launch(**kwargs):
            return types.SimpleNamespace(close=self._close)

        return types.SimpleNamespace(chromium=types.SimpleNamespace(launch=launch))

    async def __aexit__(self, *exc):
        return False

    async def _close(self):
        pass


def _fake_site(pages):
    async def fake(browser, website, tags, ace_config):
        return {
            "url": website, "base_url": "https://example.com", "timestamp": datetime.now(timezone.utc).isoformat(),
            "report": {"violations": pages[website], "incomplete": [], "passes": []},
            "links": [], "videos": [], "imgs": [], "tabable": True, "photo": None, "tags": ["wcag2a"],
        }

    return fake


@pytest.fixture()
def crawl(monkeypatch):
    """Run generate_reports offline, refusing to let any email out."""

    def no_mail(self, *args, **kwargs):
        raise AssertionError("a scan must not send mail")

    monkeypatch.setattr(scan_mod, "check_url", lambda url: True)
    monkeypatch.setattr(scan_mod, "load_robots", lambda url: None)
    monkeypatch.setattr(scan_mod, "async_playwright", _FakePlaywright)
    monkeypatch.setattr(emails_mod.AccessEmails, "send", no_mail)
    monkeypatch.setattr(emails_mod.AccessEmails, "send_each", no_mail)

    def run(website, pages):
        monkeypatch.setattr(scan_mod, "generate_report", _fake_site(pages))
        asyncio.run(scan_mod.generate_reports(website.url, task_id="t"))

    return run


def test_a_finished_crawl_records_completed_and_sends_nothing(app, make_user, make_website, crawl):
    website = make_website(make_user())
    website.should_email = True
    website.last_scan_status = "failed"
    website.last_scan_error = "boom"
    db.session.commit()

    crawl(website, {"https://example.com/": [_rule("image-alt", "critical", (("#img", "<img>"),))]})

    db.session.expire_all()
    website = db.session.get(website_models.Website, website.id)
    assert website.last_scan_status == "completed" and website.last_scan_error is None
    assert website.last_scanned is not None
    assert website.last_notified is None

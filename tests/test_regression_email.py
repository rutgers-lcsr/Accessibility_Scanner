"""Regression alerts: the rule, which email a scan sends, the website's notification
switch, and the delta block in the scan-finished email."""
import asyncio
import types
from datetime import datetime, timedelta, timezone

import pytest

import models.website as website_models
import scanner.scan as scan_mod
from mail.emails import ScanFinishedEmail, ScanRegressionEmail
from services.findings import is_regression, refresh_suppressed_counts, sync_report_findings


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setattr(website_models, "is_valid_url", lambda url: True)


def _rule(rule_id, impact="serious", nodes=(("#a", "<p>a</p>"),)):
    return {"id": rule_id, "impact": impact, "help": f"Fix {rule_id}", "helpUrl": "https://x",
            "nodes": [{"target": [s], "html": h} for s, h in nodes]}


def _scan(add_report, site, violations, when):
    from models import db

    report = add_report(site, when=when, violations=violations)
    sync_report_findings(site.id, report.id, report.timestamp, violations)
    refresh_suppressed_counts(site.id, report.id)
    db.session.commit()
    return report


def test_is_regression_rules():
    baseline = {"since": None, "new": [{"impact": "critical"}], "previous": {"total": 0}, "current": {"total": 5}}
    assert is_regression(baseline) is False
    assert is_regression({"since": "x", "new": [{"impact": "serious"}], "previous": {"total": 5}, "current": {"total": 5}}) is True
    assert is_regression({"since": "x", "new": [], "previous": {"total": 3}, "current": {"total": 4}}) is True
    assert is_regression({"since": "x", "new": [{"impact": "minor"}], "previous": {"total": 4}, "current": {"total": 3}}) is False


# --- the scan decides which email to send ------------------------------------------------


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
    """Run generate_reports offline and record which notification classes sent mail."""
    sent = []

    class RecordingFinished(ScanFinishedEmail):
        def send(self, *args, **kwargs):
            sent.append(("finished", bool(self.messages) if hasattr(self, "messages") else None))
            result = super().send(*args, **kwargs)
            sent[-1] = ("finished", len(getattr(self, "messages", []) or []))
            return result

    class RecordingRegression(ScanRegressionEmail):
        def send(self, *args, **kwargs):
            result = super().send(*args, **kwargs)
            sent.append(("regression", len(getattr(self, "messages", []) or [])))
            return result

    monkeypatch.setattr(scan_mod, "check_url", lambda url: True)
    monkeypatch.setattr(scan_mod, "load_robots", lambda url: None)
    monkeypatch.setattr(scan_mod, "async_playwright", _FakePlaywright)
    monkeypatch.setattr(scan_mod, "ScanFinishedEmail", RecordingFinished)
    monkeypatch.setattr(scan_mod, "ScanRegressionEmail", RecordingRegression)

    def run(website, pages):
        monkeypatch.setattr(scan_mod, "generate_report", _fake_site(pages))
        asyncio.run(scan_mod.generate_reports(website.url, task_id="t"))
        return sent

    return run


def test_first_scan_sends_finished_and_a_new_critical_later_sends_regression(app, make_user, make_website, crawl):
    from models import db

    website = make_website(make_user())
    website.should_email = True
    db.session.commit()
    home = "https://example.com/"

    sent = crawl(website, {home: [_rule("region", "minor")]})
    assert sent == [("finished", 0)]  # one minor issue is below the thresholds
    website = db.session.get(website_models.Website, website.id)
    assert website.last_notified is None

    sent = crawl(website, {home: [_rule("region", "minor"), _rule("image-alt", "critical", (("#img", "<img>"),))]})
    assert sent[-1] == ("regression", 1)
    db.session.expire_all()
    website = db.session.get(website_models.Website, website.id)
    assert website.last_notified is not None
    assert website.last_scan_status == "completed"


def test_regression_email_respects_the_website_switch_and_renders_the_new_rules(app, make_user, make_website, add_site, add_report):
    from models import db

    now = datetime.now(timezone.utc)
    website = make_website(make_user())
    site = add_site(website, page="/")
    _scan(add_report, site, [], now - timedelta(days=7))
    _scan(add_report, site, [_rule("image-alt", "critical", (("#img", "<img>"),))], now)
    from services.findings import changes_for_sites
    changes = changes_for_sites([site.id])
    assert changes["regression"] is True

    website.should_email = False
    assert ScanRegressionEmail(website, changes).send() is False
    assert website.last_notified is None

    website.should_email = True
    sender = ScanRegressionEmail(website, changes)
    assert sender.send() is True
    assert website.last_notified is not None
    assert "regression" in sender.msg.subject and "1 new violation" in sender.msg.subject
    html = sender.msg.html
    assert "image-alt" in html and "Critical" in html
    assert f"/reports/{changes['new'][0]['pages'][0]['report_id']}?rule=image-alt" in html
    assert f"/websites/{website.id}?tab=changes" in html
    assert "unsubscribe/?token=" in html


def test_scan_finished_email_shows_the_delta(app, make_user, make_website, add_site, add_report):
    now = datetime.now(timezone.utc)
    website = make_website(make_user())
    site = add_site(website, page="/")
    _scan(add_report, site, [_rule("region"), _rule("label", "minor", (("#l", "<input>"),))], now - timedelta(days=7))
    _scan(add_report, site, [_rule("region")], now)

    sender = ScanFinishedEmail(website)
    sender.send(force=True)

    assert sender.changes["fixed_count"] == 1
    assert "Since the previous scan" in sender.msg.html
    assert "2 → 1" in sender.msg.html and "1 fixed" in sender.msg.html

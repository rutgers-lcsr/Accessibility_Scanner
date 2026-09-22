"""Weekly admin digest: what it reports, who gets it, the on/off setting, the schedule."""
from datetime import datetime, timedelta, timezone

import pytest

import models.website as website_models
from mail.emails import AdminDigestEmail
from services.findings import refresh_suppressed_counts, sync_report_findings
from services.overview import build_digest


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setattr(website_models, "is_valid_url", lambda url: True)


def _rule(rule_id, impact="serious"):
    return {"id": rule_id, "impact": impact, "help": f"Fix {rule_id}", "helpUrl": "https://x",
            "nodes": [{"target": ["#a"], "html": "<p>"}]}


def _scan(add_report, site, violations, when):
    from models import db

    report = add_report(site, when=when, violations=violations)
    sync_report_findings(site.id, report.id, report.timestamp, violations)
    refresh_suppressed_counts(site.id, report.id)
    db.session.commit()
    return report


def _seed(make_user, make_website, add_site, add_report):
    """better: 3 → 1 violations; worse: 1 → 2; fresh: first audit this week; down: unreachable;
    idle: never scanned. All created now, so all are new this period."""
    from models import db

    now = datetime.now(timezone.utc)
    admin = make_user("root", is_admin=True)
    better = make_website(admin, base="https://better.example")
    worse = make_website(admin, base="https://worse.example")
    fresh = make_website(admin, base="https://fresh.example")
    down = make_website(admin, base="https://down.example")
    idle = make_website(admin, base="https://idle.example")
    for w in (better, worse, fresh, down):
        w.last_scanned = now
        w.last_scan_status = "completed"
    down.last_scan_status = "unreachable"
    down.last_scan_error = "connection refused"
    _scan(add_report, add_site(better, page="/"), [_rule("r1"), _rule("r2"), _rule("r3")], now - timedelta(days=10))
    _scan(add_report, better.sites.first(), [_rule("r1")], now)
    _scan(add_report, add_site(worse, page="/"), [_rule("r1")], now - timedelta(days=10))
    _scan(add_report, worse.sites.first(), [_rule("r1"), _rule("image-alt", "critical")], now)
    _scan(add_report, add_site(fresh, page="/"), [_rule("r1")], now)
    db.session.commit()
    return admin


def test_build_digest_reports_movers_first_audits_failures_and_idle_websites(app, make_user, make_website, add_site, add_report):
    _seed(make_user, make_website, add_site, add_report)

    digest = build_digest(days=7)

    assert digest["websites_count"] == 5 and digest["scanned_this_period"] == 4
    assert [(m["url"], m["previous"], m["current"]) for m in digest["movers_up"]] == [("https://worse.example", 1, 2)]
    assert [(m["url"], m["delta"]) for m in digest["movers_down"]] == [("https://better.example", -2)]
    assert [w["url"] for w in digest["newly_audited"]] == ["https://fresh.example"]
    assert [(w["url"], w["status"], w["error"]) for w in digest["failing"]] == [("https://down.example", "unreachable", "connection refused")]
    assert [w["url"] for w in digest["never_scanned"]] == ["https://idle.example"]
    assert len(digest["new_websites"]) == 5
    assert digest["totals"]["violations"]["total"] == 4 and digest["top_rules"][0]["id"] == "image-alt"


def test_digest_email_goes_to_admins_only_when_there_is_something_to_say(app, make_user, make_website, add_site, add_report):
    assert AdminDigestEmail().send() is False  # no admins, no websites

    _seed(make_user, make_website, add_site, add_report)
    sender = AdminDigestEmail()
    assert sender.send() is True
    assert sender.msg.recipients == ["root@rutgers.edu"]
    html = sender.msg.html
    assert "Got worse" in html and "https://worse.example" in html
    assert "Unreachable" in html and "connection refused" in html
    assert "Never scanned" in html and "https://idle.example" in html
    assert "/dashboard" in html


def test_digest_task_respects_the_setting(app, make_user, make_website, add_site, add_report):
    from models.settings import Settings
    from scanner.tasks import send_admin_digest

    _seed(make_user, make_website, add_site, add_report)
    Settings.set("admin_digest_enabled", "false")
    assert send_admin_digest.run() == {"sent": False, "recipients": 0}

    Settings.set("admin_digest_enabled", "true")
    assert send_admin_digest.run() == {"sent": True, "recipients": 1}


def test_beat_schedules_the_digest():
    from celery.schedules import crontab

    from celery_app import celery

    entry = celery.conf.beat_schedule["admin-weekly-digest"]
    assert entry["task"] == "scanner.tasks.send_admin_digest"
    assert isinstance(entry["schedule"], crontab)

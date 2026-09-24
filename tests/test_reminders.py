"""Reminders: a website with open critical or serious issues and no activity gets a firmer
digest after a period, once per period; after a second period the website admin's copy
is also sent to the escalation address. Looking at the report does not reset the clock."""
from datetime import datetime, timedelta, timezone

import pytest

import models.website as website_models
import services.owner_digest as digest_mod
from models import db
from models.notifications import WebsiteView
from services.findings import refresh_suppressed_counts, set_finding_status, sync_report_findings
from services.owner_digest import reminder_due, run_owner_digests

SETTINGS = {'enabled': True, 'after_days': 30, 'escalate_days': 60, 'email': 'chair@example.edu'}
SERIOUS = {'total': 2, 'critical': 1, 'serious': 1, 'moderate': 0, 'minor': 0}
MINOR = {'total': 2, 'critical': 0, 'serious': 0, 'moderate': 1, 'minor': 1}


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setattr(website_models, "is_valid_url", lambda url: True)


def _rule(rule_id, impact="critical", selector="#a"):
    return {"id": rule_id, "impact": impact, "help": f"Fix {rule_id}", "helpUrl": "https://x",
            "nodes": [{"target": [selector], "html": f"<p>{selector}</p>"}]}


def _scan(add_report, site, violations, when=None):
    report = add_report(site, when=when, violations=violations)
    sync_report_findings(site.id, report.id, report.timestamp, violations)
    refresh_suppressed_counts(site.id, report.id)
    db.session.commit()
    return report


def test_the_streak_starts_at_the_last_email_and_a_reminder_follows_the_period(app, make_user, make_website):
    website = make_website(make_user())
    told = datetime(2026, 9, 1)
    website.last_notified = told

    assert reminder_due(website, SERIOUS, None, SETTINGS, told + timedelta(days=10)) is None
    assert website.attention_since == told
    assert reminder_due(website, SERIOUS, None, SETTINGS, told + timedelta(days=30)) == 'reminder'
    website.last_reminded_at = told + timedelta(days=30)
    assert reminder_due(website, SERIOUS, None, SETTINGS, told + timedelta(days=40)) is None  # once per period
    assert reminder_due(website, SERIOUS, None, SETTINGS, told + timedelta(days=60)) == 'escalation'
    assert reminder_due(website, SERIOUS, None, {**SETTINGS, 'email': ''}, told + timedelta(days=60)) == 'reminder'


def test_only_critical_or_serious_issues_and_only_after_a_first_digest(app, make_user, make_website):
    website = make_website(make_user())
    website.last_notified = None
    assert reminder_due(website, SERIOUS, None, SETTINGS, datetime(2026, 12, 1)) is None
    website.last_notified = datetime(2026, 9, 1)
    assert reminder_due(website, MINOR, None, SETTINGS, datetime(2026, 12, 1)) is None
    assert website.attention_since is None


def test_activity_resets_the_streak_but_a_page_view_does_not(app, make_user, make_website):
    website = make_website(make_user())
    told = datetime(2026, 9, 1)
    website.last_notified = told
    website.attention_since = told
    website.last_reminded_at = told + timedelta(days=30)
    website.reminder_count = 1
    website.escalated_at = told + timedelta(days=60)

    assert reminder_due(website, SERIOUS, told + timedelta(days=5), SETTINGS, told + timedelta(days=70)) is None
    assert website.attention_since is None and website.reminder_count == 0 and website.escalated_at is None

    website.last_notified = told
    assert reminder_due(website, SERIOUS, None, SETTINGS, told + timedelta(days=31)) == 'reminder'  # a view is not activity


def test_run_reminds_then_escalates_the_admins_copy_only(app, make_user, make_website, add_site, add_report, monkeypatch):
    monkeypatch.setattr(digest_mod, "reminder_settings", lambda: dict(SETTINGS))
    from mail.emails import OwnerDigestEmail
    sent = []
    monkeypatch.setattr(OwnerDigestEmail, "send", lambda self: sent.append(self) or True)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    alice = make_user("alice")
    bob = make_user("bob")
    website = make_website(alice)
    website.users.append(bob)
    site = add_site(website, page="/")
    _scan(add_report, site, [_rule("image-alt", "critical", "#i")], when=now)
    website.last_scanned = now
    db.session.commit()

    first = run_owner_digests(now=now + timedelta(hours=1))
    assert first["sent"] == 2 and first["reminders"] == 0
    assert {(m.tone, m.cc) for m in sent} == {('first', None)}
    sent.clear()

    WebsiteView.touch(alice.id, website.id, now=now + timedelta(days=20))  # looked, did nothing
    reminded = run_owner_digests(now=now + timedelta(days=31))
    assert reminded["sent"] == 2 and reminded["reminders"] == 1 and website.reminder_count == 1
    assert {m.tone for m in sent} == {'reminder'} and all(m.cc is None for m in sent)
    assert website.attention_since is not None
    sent.clear()

    assert run_owner_digests(now=now + timedelta(days=40))["sent"] == 0  # once per period

    escalated = run_owner_digests(now=now + timedelta(days=61))
    assert escalated["escalations"] == 1 and website.escalated_at is not None
    by_user = {m.user.username: m for m in sent}
    assert by_user["alice"].tone == 'escalation' and by_user["alice"].cc == ['chair@example.edu']
    assert by_user["bob"].tone == 'escalation' and by_user["bob"].cc is None
    assert by_user["alice"].digest["websites"][0]["escalated"] is True
    assert by_user["alice"].digest["escalation_email"] == "chair@example.edu"
    sent.clear()

    set_finding_status(site.findings.filter_by(selector="#i").one(), "accepted", None, alice.id)
    db.session.commit()
    after = run_owner_digests(now=now + timedelta(days=92))
    assert website.attention_since is None and website.reminder_count == 0 and website.escalated_at is None
    assert after["reminders"] == 0 and after["escalations"] == 0

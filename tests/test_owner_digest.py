"""Owner digests: one email per person over their websites, measured since that person's
last digest, sent only when something changed, leading with the fixes that clear the most
pages, with a text part, unsubscribe headers and the policy note."""
from datetime import datetime, timedelta, timezone

import pytest

import mail.emails as emails_mod
import models.website as website_models
from mail.emails import OwnerDigestEmail
from models import db
from models.notifications import WebsiteView
from services.findings import refresh_suppressed_counts, sync_report_findings
from services.owner_digest import build_owner_digest, digest_changed, digest_users, run_owner_digests, send_website_digest


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setattr(website_models, "is_valid_url", lambda url: True)


def _rule(rule_id, impact="serious", selectors=("#a",)):
    return {"id": rule_id, "impact": impact, "help": f"Fix {rule_id}", "helpUrl": f"https://x/{rule_id}",
            "nodes": [{"target": [s], "html": f"<p>{s}</p>"} for s in selectors]}


def _scan(add_report, site, violations, when=None):
    report = add_report(site, when=when, violations=violations)
    sync_report_findings(site.id, report.id, report.timestamp, violations)
    refresh_suppressed_counts(site.id, report.id)
    db.session.commit()
    return report


def _naive(when):
    return when.replace(tzinfo=None)


def test_first_digest_leads_with_the_fixes_that_clear_the_most_pages(app, make_user, make_website, add_site, add_report):
    alice = make_user("alice")
    website = make_website(alice, base="https://example.com")
    home, about = add_site(website, page="/"), add_site(website, page="/about")
    _scan(add_report, home, [_rule("region", "moderate", ("#r1", "#r2", "#r3")), _rule("image-alt", "critical", ("#i",))])
    _scan(add_report, about, [_rule("region", "moderate", ("#r1",))])

    digest = build_owner_digest(alice, [website], None)

    assert digest["engagement"] == "never_opened" and digest["since"] is None
    assert digest["totals"]["violations"] == 3 and digest["totals"]["pages_with_issues"] == 2
    first = digest["fix_first"][0]
    assert first["rule_id"] == "region" and first["pages"] == 2 and first["occurrences"] == 4
    assert first["link"].endswith(f"/websites/{website.id}?tab=fix&rule=region")
    assert first["guide"].endswith("/help/fix/region") and digest["fix_first"][1]["guide"].endswith("/help/fix/image-alt")
    assert digest["websites"][0]["show"] is True
    assert digest_changed(digest) is True


def test_change_is_measured_since_the_persons_last_digest(app, make_user, make_website, add_site, add_report):
    now = datetime.now(timezone.utc)
    alice = make_user("alice")
    website = make_website(alice)
    site = add_site(website, page="/")
    rules = [_rule("region", "moderate", ("#r",)), _rule("image-alt", "critical", ("#i",)), _rule("label", "critical", ("#l",))]
    _scan(add_report, site, rules, when=now - timedelta(days=10))
    _scan(add_report, site, rules[:1], when=now)
    website.last_scanned = _naive(now)
    db.session.commit()

    digest = build_owner_digest(alice, [website], _naive(now - timedelta(days=5)))
    row = digest["websites"][0]
    assert (row["previous_violations"], row["violations"]["total"]) == (3, 1)
    assert row["fixed_since"] == 2 and digest["totals"]["fixed_since"] == 2
    assert digest["engagement"] == "fixed"
    assert digest_changed(digest) is True

    later = build_owner_digest(alice, [website], _naive(now + timedelta(minutes=1)))
    assert later["websites"][0]["scanned_since"] is False
    assert digest_changed(later) is False


def test_engagement_wording_follows_what_the_person_did(app, make_user, make_website, add_site, add_report):
    now = datetime.now(timezone.utc)
    alice = make_user("alice")
    website = make_website(alice)
    _scan(add_report, add_site(website, page="/"), [_rule("region")], when=now - timedelta(days=3))
    since = _naive(now - timedelta(days=2))

    assert build_owner_digest(alice, [website], since)["engagement"] == "never_opened"
    WebsiteView.touch(alice.id, website.id, now=_naive(now - timedelta(days=4)))
    assert build_owner_digest(alice, [website], since)["engagement"] == "not_since_last_email"
    WebsiteView.touch(alice.id, website.id, now=_naive(now - timedelta(days=1)))
    assert build_owner_digest(alice, [website], since)["engagement"] == "looked_no_change"


def test_run_sends_one_digest_per_person_and_only_when_something_changed(app, make_user, make_website, add_site, add_report):
    now = datetime.now(timezone.utc)
    alice = make_user("alice")
    bob = make_user("bob")
    first = make_website(alice, base="https://one.example.com")
    second = make_website(alice, base="https://two.example.com")
    first.users.append(bob)
    db.session.commit()
    for website in (first, second):
        _scan(add_report, add_site(website, page="/"), [_rule("region")], when=now)
        website.last_scanned = _naive(now)
    db.session.commit()
    assert {u.username for u in digest_users()} == {"alice", "bob"}

    result = run_owner_digests(now=_naive(now + timedelta(hours=1)))

    assert (result["users"], result["sent"], result["skipped"]) == (2, 2, 0)
    assert alice.last_digest_at is not None and bob.last_digest_at is not None
    assert first.last_notified is not None and second.last_notified is not None

    again = run_owner_digests(now=_naive(now + timedelta(days=2)))
    assert again["sent"] == 0 and again["skipped"] == 2  # nothing changed for anyone

    _scan(add_report, second.sites.first(), [], when=now + timedelta(days=3))  # region got fixed on two.example.com
    second.last_scanned = _naive(now + timedelta(days=3))
    db.session.commit()
    third = run_owner_digests(now=_naive(now + timedelta(days=3, hours=1)))
    assert third["sent"] == 1  # alice only: bob is not on that website


def test_a_clean_website_does_not_start_a_digest(app, make_user, make_website, add_site, add_report):
    now = datetime.now(timezone.utc)
    alice = make_user("alice")
    website = make_website(alice)
    site = add_site(website, page="/")
    _scan(add_report, site, [], when=now)
    website.last_scanned = _naive(now)
    db.session.commit()

    assert run_owner_digests(now=_naive(now + timedelta(hours=1)))["sent"] == 0
    assert alice.last_digest_at is None

    _scan(add_report, site, [], when=now + timedelta(days=2))  # still clean on the next scan
    website.last_scanned = _naive(now + timedelta(days=2))
    db.session.commit()
    assert run_owner_digests(now=_naive(now + timedelta(days=2, hours=1)))["sent"] == 0


def test_fixing_everything_still_sends(app, make_user, make_website, add_site, add_report):
    now = datetime.now(timezone.utc)
    alice = make_user("alice")
    website = make_website(alice)
    site = add_site(website, page="/")
    _scan(add_report, site, [_rule("region")], when=now)
    website.last_scanned = _naive(now)
    db.session.commit()
    assert run_owner_digests(now=_naive(now + timedelta(hours=1)))["sent"] == 1

    _scan(add_report, site, [], when=now + timedelta(days=2))
    website.last_scanned = _naive(now + timedelta(days=2))
    db.session.commit()
    result = run_owner_digests(now=_naive(now + timedelta(days=2, hours=1)), dry_run=True)
    assert result["sent"] == 1 and ": update: " in result["details"][0]


def test_never_scanned_websites_are_left_out_of_the_email(app, make_user, make_website, add_site, add_report):
    now = datetime.now(timezone.utc)
    alice = make_user("alice")
    scanned = make_website(alice, base="https://one.example.com")
    make_website(alice, base="https://two.example.com")  # watched, never scanned
    _scan(add_report, add_site(scanned, page="/"), [_rule("region")], when=now)
    scanned.last_scanned = _naive(now)
    db.session.commit()

    digest = build_owner_digest(alice, sorted(alice.admin_websites, key=lambda w: w.url), None)

    shown = [row["host"] for row in digest["websites"] if row["show"]]
    assert shown == ["one.example.com"] and digest["hidden_websites"] == 0
    email = OwnerDigestEmail(alice, digest, tone="first")
    assert email.send() and "two.example.com" not in email.msg.body and "Not scanned yet" not in email.msg.body


def test_run_is_idempotent_within_a_day(app, make_user, make_website, add_site, add_report):
    now = datetime.now(timezone.utc)
    website = make_website(make_user("alice"))
    _scan(add_report, add_site(website, page="/"), [_rule("region")], when=now)
    website.last_scanned = _naive(now)
    db.session.commit()

    assert run_owner_digests(now=_naive(now + timedelta(hours=1)))["sent"] == 1
    assert run_owner_digests(now=_naive(now + timedelta(hours=2)))["sent"] == 0
    assert run_owner_digests(now=_naive(now + timedelta(hours=2)), user_ids=[website.admin_id])["sent"] == 1  # by hand


def test_respects_the_website_switch_and_opt_outs(app, make_user, make_website, add_site, add_report):
    alice = make_user("alice")
    bob = make_user("bob")
    website = make_website(alice)
    website.users.append(bob)
    _scan(add_report, add_site(website, page="/"), [_rule("region")])
    website.last_scanned = datetime.now(timezone.utc).replace(tzinfo=None)
    website.set_subscribed(bob, False)

    assert [u.username for u in digest_users()] == ["alice"]
    website.should_email = False
    db.session.commit()
    assert digest_users() == []


def test_message_has_text_part_headers_policy_and_the_scan_time(app, make_user, make_website, add_site, add_report):
    alice = make_user("alice")
    website = make_website(alice)
    _scan(add_report, add_site(website, page="/"), [_rule("region")])
    website.last_scanned = datetime(2026, 9, 20, 3, 10)
    db.session.commit()

    email = OwnerDigestEmail(alice, build_owner_digest(alice, [website], None), tone="first")
    assert email.send()

    msg = email.msg
    assert msg.body and "FIX THESE FIRST" in msg.body and "Fix these first" in msg.html
    assert "Policy 70.1.5" in msg.html and "Policy 70.1.5" in msg.body
    assert "Sep 20, 2026" in msg.html and "Sep 20, 2026" in msg.body
    assert msg.extra_headers["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"
    assert "unsubscribe/?token=" in msg.extra_headers["List-Unsubscribe"]
    assert f"/websites/{website.id}?tab=fix&rule=region" in msg.body
    assert f"/websites/{website.id}?tab=fix&amp;rule=region" in msg.html  # escaped in HTML
    assert "/help/fix/region" in msg.html


def test_subject_lines_say_what_changed(app, make_user, make_website, add_site, add_report):
    now = datetime.now(timezone.utc)
    alice = make_user("alice")
    website = make_website(alice, base="https://cs.example.com")
    site = add_site(website, page="/")
    _scan(add_report, site, [_rule("region", "serious", ("#r",)), _rule("image-alt", "critical", ("#i",))], when=now - timedelta(days=10))
    _scan(add_report, site, [_rule("region", "serious", ("#r",)), _rule("link-name", "serious", ("#k",))], when=now)
    website.last_scanned = _naive(now)
    db.session.commit()
    since = _naive(now - timedelta(days=5))

    subject = lambda tone, since_=since: OwnerDigestEmail(alice, build_owner_digest(alice, [website], since_), tone=tone).subject()
    assert subject("first", None) == "Accessibility report for cs.example.com: 2 issues on 1 pages"
    assert subject("update") == "cs.example.com: 1 fixed, 1 new accessibility issues"
    assert subject("no_change") == "No change on cs.example.com: 2 open accessibility issues"
    assert subject("reminder") == "Reminder: cs.example.com still has 2 critical or serious accessibility issues"
    assert subject("escalation") == "Action required: cs.example.com still has 2 critical or serious accessibility issues"


def test_forced_website_send_reaches_every_recipient_and_the_extra_address(app, make_user, make_website, add_site, add_report):
    alice = make_user("alice")
    bob = make_user("bob")
    website = make_website(alice)
    website.users.append(bob)
    _scan(add_report, add_site(website, page="/"), [_rule("region")])

    assert send_website_digest(website, email="dean@example.org") == 3
    assert website.last_notified is not None
    assert alice.last_digest_at is None and bob.last_digest_at is None


def test_state_is_stamped_only_on_delivery(app, make_user, make_website, add_site, add_report, monkeypatch):
    now = datetime.now(timezone.utc)
    website = make_website(make_user("alice"))
    _scan(add_report, add_site(website, page="/"), [_rule("region")], when=now)
    website.last_scanned = _naive(now)
    db.session.commit()
    monkeypatch.setattr(emails_mod, "TESTING", False)
    monkeypatch.setattr(emails_mod.mail, "send", lambda msg: (_ for _ in ()).throw(RuntimeError("smtp down")))

    result = run_owner_digests(now=_naive(now + timedelta(hours=1)))

    assert result["sent"] == 0 and website.admin.last_digest_at is None and website.last_notified is None


def test_dry_run_reports_without_sending_or_stamping(app, make_user, make_website, add_site, add_report):
    now = datetime.now(timezone.utc)
    website = make_website(make_user("alice"))
    _scan(add_report, add_site(website, page="/"), [_rule("region")], when=now)
    website.last_scanned = _naive(now)
    db.session.commit()

    result = run_owner_digests(now=_naive(now + timedelta(hours=1)), dry_run=True)

    assert result["sent"] == 1 and result["details"] and "first" in result["details"][0]
    assert website.admin.last_digest_at is None and website.last_notified is None


def test_task_respects_the_setting_and_beat_schedules_it_daily(app, make_user, make_website, add_site, add_report):
    from celery.schedules import crontab
    from celery_app import celery
    from models.settings import Settings
    from scanner.tasks import send_owner_digests

    website = make_website(make_user("alice"))
    _scan(add_report, add_site(website, page="/"), [_rule("region")])
    website.last_scanned = datetime.now(timezone.utc).replace(tzinfo=None)
    db.session.commit()

    Settings.set("owner_digest_enabled", "false")
    assert send_owner_digests.run()["disabled"] is True and website.last_notified is None
    Settings.set("owner_digest_enabled", "true")
    assert send_owner_digests.run()["sent"] == 1 and website.last_notified is not None

    entry = celery.conf.beat_schedule["owner-digests"]
    assert entry["task"] == "scanner.tasks.send_owner_digests"
    assert isinstance(entry["schedule"], crontab)

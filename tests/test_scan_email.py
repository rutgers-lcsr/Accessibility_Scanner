"""The scan-finished email: subject, top issues, worst pages, coverage, the delta since
the previous scan and since the last email, failure wording, and per-recipient links."""
from datetime import datetime, timedelta, timezone

import pytest

import models.website as website_models
from mail.emails import ScanFinishedEmail
from services.findings import refresh_suppressed_counts, sync_report_findings
from services.overview import scan_summary


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setattr(website_models, "is_valid_url", lambda url: True)


def _rule(rule_id, impact="serious", nodes=(("#a", "<p>a</p>"),)):
    return {"id": rule_id, "impact": impact, "help": f"Fix {rule_id}", "helpUrl": f"https://help/{rule_id}",
            "nodes": [{"target": [s], "html": h} for s, h in nodes]}


def _scan(add_report, site, violations, when=None):
    from models import db

    report = add_report(site, when=when, violations=violations)
    sync_report_findings(site.id, report.id, report.timestamp, violations)
    refresh_suppressed_counts(site.id, report.id)
    db.session.commit()
    return report


def test_summary_covers_counts_top_issues_worst_pages_and_coverage(app, make_user, make_website, add_site, add_report):
    now = datetime.now(timezone.utc)
    website = make_website(make_user())
    website.last_scan_status = "completed"
    home = add_site(website, page="/")
    about = add_site(website, page="/about")
    broken = add_site(website, page="/broken")
    broken.last_scan_status = "failed"
    _scan(add_report, home, [_rule("image-alt", "critical", (("#a", "<img>"), ("#b", "<img>"))), _rule("region", "moderate", (("#r", "<div>"),))], now)
    _scan(add_report, about, [_rule("image-alt", "critical", (("#c", "<img>"),))], now)

    summary = scan_summary(website)

    assert summary["violations"] == {"total": 3, "critical": 2, "serious": 0, "moderate": 1, "minor": 0}
    assert (summary["pages_total"], summary["pages_audited"], summary["pages_failed"]) == (3, 2, 1)
    assert [r["id"] for r in summary["top_issues"]] == ["image-alt", "region"]
    assert summary["top_issues"][0]["pages"] == 2 and summary["top_issues"][0]["occurrences"] == 3
    assert [p["url"] for p in summary["worst_pages"]] == [home.url, about.url]
    assert summary["since_last_email"] is None


def test_email_lists_issues_pages_and_deltas_with_a_personal_link(app, make_user, make_website, add_site, add_report):
    from models import db

    now = datetime.now(timezone.utc)
    website = make_website(make_user())
    website.last_scan_status = "completed"
    website.last_notified = (now - timedelta(days=3)).replace(tzinfo=None)
    site = add_site(website, page="/")
    _scan(add_report, site, [_rule("region", "moderate", (("#r", "<div>"),)), _rule("label", "minor", (("#l", "<input>"),))], now - timedelta(days=7))
    _scan(add_report, site, [_rule("region", "moderate", (("#r", "<div>"),)), _rule("image-alt", "critical", (("#img", "<img>"),))], now)
    db.session.commit()

    sender = ScanFinishedEmail(website)
    sender.send(force=True)

    assert sender.msg.subject == "Accessibility scan finished: example.com: 2 violations (1 critical)"
    html = sender.msg.html
    assert "Fix image-alt" in html and f"/websites/{website.id}?tab=violations&rule=image-alt" in html
    assert "https://help/image-alt" in html
    assert f"/reports/{site.get_recent_report()['id']}" in html
    assert "Since the previous scan" in html and "1 new" in html and "1 fixed" in html
    assert "Since your last email" in html and "2 → 2" in html
    assert "1 of 1 pages audited" in html
    assert "unsubscribe/?token=" in html


def test_unreachable_scan_email_says_so_and_skips_the_tables(app, make_user, make_website, add_site, add_report):
    website = make_website(make_user())
    website.last_scan_status = "unreachable"
    website.last_scan_error = "The website did not respond to the reachability check"
    _scan(add_report, add_site(website, page="/"), [_rule("region")])

    sender = ScanFinishedEmail(website)
    sender.send(force=True)

    assert sender.msg.subject == "Accessibility scan unreachable: example.com"
    html = sender.msg.html
    assert "could not reach the website" in html and "did not respond" in html
    assert "Top issues" not in html and "Pages with the most issues" not in html


def test_nothing_is_sent_without_recipients(app, make_user, make_website, add_site, add_report):
    website = make_website(make_user())
    website.set_subscribed(website.admin, False)
    _scan(add_report, add_site(website, page="/"), [_rule("region")])

    sender = ScanFinishedEmail(website)
    sender.send(force=True)

    assert getattr(sender, "messages", []) == [] and website.last_notified is None

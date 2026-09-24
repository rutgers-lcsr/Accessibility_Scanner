"""Findings: identity across scans, the sync rules (new / unchanged / fixed / reopened /
sticky suppression), the suppression snapshot, the scanner write path and the backfill."""
import asyncio
import types
from datetime import datetime, timedelta, timezone

import pytest

import models.website as website_models
import scanner.scan as scan_mod
from models.finding import Finding
from services.findings import (
    backfill_latest,
    fingerprint,
    normalise_selector,
    suppressed_counts_for,
    sync_report_findings,
)


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setattr(website_models, "is_valid_url", lambda url: True)


def _rule(rule_id, impact="serious", nodes=(("#a", "<p>a</p>"),)):
    return {
        "id": rule_id,
        "impact": impact,
        "help": f"Fix {rule_id}",
        "helpUrl": f"https://example.com/rules/{rule_id}",
        "nodes": [{"target": [selector], "html": html} for selector, html in nodes],
    }


def _sync(site, report):
    from models import db

    result = sync_report_findings(site.id, report.id, report.timestamp, report.report["violations"])
    db.session.commit()
    return result


def _findings(site):
    return {f.fingerprint: f for f in site.findings.all()}


# --- identity ----------------------------------------------------------------------------


def test_fingerprint_is_stable_and_selector_normalised():
    assert normalise_selector([" #a ", ["#shadow", "  span"]]) == "#a >>> #shadow >>> span"
    assert normalise_selector(None) == "" and normalise_selector([]) == ""
    assert fingerprint("image-alt", "#a") == fingerprint("image-alt", "#a")
    assert fingerprint("image-alt", "#a") != fingerprint("image-alt", "#b")
    assert fingerprint("image-alt", "#a") != fingerprint("color-contrast", "#a")


# --- sync rules --------------------------------------------------------------------------


def test_first_scan_creates_open_findings(app, make_user, make_site, add_report):
    site = make_site(make_user())
    report = add_report(site, violations=[_rule("image-alt", "critical", (("#hero", "<img>"), ("#logo", "<img>"))), _rule("region")])

    result = _sync(site, report)

    assert (result.new, result.closed, result.reopened, result.unchanged) == (3, 0, 0, 0)
    findings = site.findings.all()
    assert {f.rule_id for f in findings} == {"image-alt", "region"}
    assert all(f.status == "open" and f.last_report_id == report.id and f.first_seen == f.last_seen for f in findings)
    hero = next(f for f in findings if f.selector == "#hero")
    assert hero.impact == "critical" and hero.help == "Fix image-alt" and hero.html == "<img>"


def test_unchanged_finding_keeps_first_seen_and_moves_last_seen(app, make_user, make_site, add_report):
    now = datetime.now(timezone.utc)
    site = make_site(make_user())
    first = add_report(site, when=now - timedelta(days=7), violations=[_rule("region")])
    _sync(site, first)
    second = add_report(site, when=now, violations=[_rule("region")])

    result = _sync(site, second)

    assert (result.new, result.unchanged, result.closed) == (0, 1, 0)
    finding = site.findings.one()
    assert finding.first_seen == first.timestamp.replace(tzinfo=None)
    assert finding.last_seen == second.timestamp.replace(tzinfo=None)
    assert finding.last_report_id == second.id


def test_missing_finding_is_auto_closed_and_returning_one_reopened(app, make_user, make_site, add_report):
    now = datetime.now(timezone.utc)
    site = make_site(make_user())
    _sync(site, add_report(site, when=now - timedelta(days=14), violations=[_rule("region")]))
    finding = site.findings.one()
    finding.note = "Talked to the owner"

    closed = _sync(site, add_report(site, when=now - timedelta(days=7), violations=[]))
    assert closed.closed == 1
    assert finding.status == "fixed" and finding.status_by is None and finding.status_at is not None

    reopened = _sync(site, add_report(site, when=now, violations=[_rule("region")]))
    assert reopened.reopened == 1
    assert finding.status == "open" and finding.note == "Talked to the owner"
    assert site.findings.count() == 1  # the same row, not a new one


def test_suppressed_status_is_sticky(app, make_user, make_site, add_report):
    now = datetime.now(timezone.utc)
    site = make_site(make_user())
    _sync(site, add_report(site, when=now - timedelta(days=14), violations=[_rule("region")]))
    finding = site.findings.one()
    finding.status = "false_positive"

    _sync(site, add_report(site, when=now - timedelta(days=7), violations=[_rule("region")]))  # still there
    assert finding.status == "false_positive"
    _sync(site, add_report(site, when=now, violations=[]))  # gone
    assert finding.status == "false_positive"


def test_nth_child_shift_is_matched_by_html(app, make_user, make_site, add_report):
    now = datetime.now(timezone.utc)
    site = make_site(make_user())
    first = add_report(site, when=now - timedelta(days=7), violations=[_rule("image-alt", nodes=(("li:nth-child(2) > img", '<img src="a.png">'),))])
    _sync(site, first)
    shifted = add_report(site, when=now, violations=[_rule("image-alt", nodes=(("li:nth-child(3) > img", '<img src="a.png">'),))])

    result = _sync(site, shifted)

    assert (result.new, result.closed, result.unchanged) == (0, 0, 1)
    finding = site.findings.one()
    assert finding.selector == "li:nth-child(3) > img"
    assert finding.fingerprint == fingerprint("image-alt", "li:nth-child(3) > img")
    assert finding.first_seen == first.timestamp.replace(tzinfo=None)


def test_ambiguous_html_is_not_rebound(app, make_user, make_site, add_report):
    now = datetime.now(timezone.utc)
    site = make_site(make_user())
    same = '<a href="#">more</a>'
    _sync(site, add_report(site, when=now - timedelta(days=7), violations=[_rule("link-name", nodes=(("#a", same), ("#b", same)))]))

    result = _sync(site, add_report(site, when=now, violations=[_rule("link-name", nodes=(("#c", same), ("#d", same)))]))

    assert (result.new, result.closed) == (2, 2)
    assert sorted(f.status for f in site.findings.all()) == ["fixed", "fixed", "open", "open"]


def test_suppressed_counts_count_fully_suppressed_rules_only(app, make_user, make_site, add_report):
    site = make_site(make_user())
    report = add_report(site, violations=[
        _rule("image-alt", "critical", (("#a", "<img>"), ("#b", "<img>"))),
        _rule("region", "moderate", (("#r", "<div>"),)),
        _rule("label", "minor", (("#l", "<input>"),)),
    ])
    _sync(site, report)
    by_selector = {f.selector: f for f in site.findings.all()}

    assert suppressed_counts_for(site.id, report.id)["total"] == 0
    by_selector["#a"].status = "false_positive"  # half of image-alt: still counts
    assert suppressed_counts_for(site.id, report.id)["total"] == 0
    by_selector["#b"].status = "accepted"
    by_selector["#a"].status = "accepted"
    assert suppressed_counts_for(site.id, report.id) == {"total": 1, "critical": 1, "serious": 0, "moderate": 0, "minor": 0}


# --- scanner write path ------------------------------------------------------------------


def _report(url, violations):
    return {
        "url": url, "base_url": "https://example.com", "timestamp": datetime.now(timezone.utc).isoformat(),
        "report": {"violations": violations, "incomplete": [], "passes": []},
        "links": [], "videos": [], "imgs": [], "tabable": True, "photo": None, "tags": ["wcag2a"],
    }


def test_store_report_writes_findings_and_the_snapshot(app, make_user, make_site):
    from models import db

    site = make_site(make_user())
    website = site.websites.first()

    asyncio.run(scan_mod.store_report_to_db(_report(site.url, [_rule("region")]), types.SimpleNamespace(id=website.id, url=website.url), app))

    db.session.expire_all()
    site = db.session.get(website_models.Site, site.id)
    assert site.findings.count() == 1
    report = site.get_full_current_report()
    assert report.suppressed_counts == {"total": 0, "critical": 0, "serious": 0, "moderate": 0, "minor": 0}


def test_sync_failure_keeps_the_report(app, make_user, make_site, monkeypatch):
    from models import db

    def boom(*args, **kwargs):
        raise RuntimeError("sync broke")

    monkeypatch.setattr(scan_mod, "sync_report_findings", boom)
    site = make_site(make_user())
    website = site.websites.first()

    asyncio.run(scan_mod.store_report_to_db(_report(site.url, [_rule("region")]), types.SimpleNamespace(id=website.id, url=website.url), app))

    db.session.expire_all()
    site = db.session.get(website_models.Site, site.id)
    report = site.get_full_current_report()
    assert report is not None and report.suppressed_counts is None
    assert site.findings.count() == 0


# --- backfill and cleanup ------------------------------------------------------------------


def test_backfill_syncs_the_latest_report_only_and_is_idempotent(app, make_user, make_site, add_report):
    from models import db

    from models.report import Report

    now = datetime.now(timezone.utc)
    site = make_site(make_user())
    add_report(site, when=now - timedelta(days=30), violations=[_rule("old-rule")])
    latest = add_report(site, when=now, violations=[_rule("region"), _rule("label")])
    site_id, latest_id = site.id, latest.id  # the backfill detaches everything it touched

    stats = backfill_latest(batch=1)

    assert stats == {"reports": 1, "new": 2, "skipped": 0}
    site = db.session.get(website_models.Site, site_id)
    assert {f.rule_id for f in site.findings.all()} == {"region", "label"}
    assert all(f.last_report_id == latest_id for f in site.findings.all())
    assert db.session.get(Report, latest_id).suppressed_counts is not None
    assert backfill_latest()["reports"] == 0  # nothing left to sync


def test_deleting_a_site_removes_its_findings(app, make_user, make_site, add_report):
    from models import db

    site = make_site(make_user())
    _sync(site, add_report(site, violations=[_rule("region")]))
    assert db.session.query(Finding).count() == 1

    db.session.delete(site)
    db.session.commit()

    assert db.session.query(Finding).count() == 0


def test_failure_summary_is_stored_normalised_and_refreshed(app, make_user, make_site, add_report):
    from models import db
    from services.findings import sync_report_findings

    site = make_site(make_user())

    def rule(summary):
        return {"id": "image-alt", "impact": "critical", "help": "Images must have alternative text",
                "helpUrl": "https://x", "nodes": [{"target": ["#img"], "html": "<img>", "failureSummary": summary}]}

    report = add_report(site, violations=[rule("Fix any of the following:\n  Element does not have an alt attribute   ")])
    sync_report_findings(site.id, report.id, report.timestamp, report.report["violations"])
    db.session.commit()
    finding = site.findings.one()
    assert finding.failure_summary == "Fix any of the following: Element does not have an alt attribute"
    assert finding.to_dict()["failure_summary"] == finding.failure_summary

    report = add_report(site, violations=[rule("x" * 1500)])
    sync_report_findings(site.id, report.id, report.timestamp, report.report["violations"])
    db.session.commit()
    assert len(site.findings.one().failure_summary) == 1000

    report = add_report(site, violations=[rule(None)])
    sync_report_findings(site.id, report.id, report.timestamp, report.report["violations"])
    db.session.commit()
    assert site.findings.one().failure_summary is None

"""Suppressed findings leave every count users see: page, website, listing order,
dashboard totals and top rules, and history from the moment of the verdict on."""
from datetime import datetime, timedelta, timezone

import pytest

import models.website as website_models
from services.findings import refresh_suppressed_counts, set_finding_status, sync_report_findings


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setattr(website_models, "is_valid_url", lambda url: True)


def _rule(rule_id, impact="serious", nodes=(("#a", "<p>a</p>"),)):
    return {"id": rule_id, "impact": impact, "help": f"Fix {rule_id}", "helpUrl": "https://x",
            "nodes": [{"target": [s], "html": h} for s, h in nodes]}


def _scan(add_report, site, violations, when=None):
    from models import db

    report = add_report(site, when=when, violations=violations)
    sync_report_findings(site.id, report.id, report.timestamp, violations)
    refresh_suppressed_counts(site.id, report.id)
    db.session.commit()
    return report


def _suppress(site, selector, status="accepted"):
    from models import db

    set_finding_status(site.findings.filter_by(selector=selector).one(), status, None, None)
    db.session.commit()


def test_page_and_website_counts_subtract_suppressed_rules(app, make_user, make_website, add_site, add_report):
    website = make_website(make_user())
    site = add_site(website, page="/")
    _scan(add_report, site, [_rule("region", "moderate"), _rule("image-alt", "critical", (("#img", "<img>"),))])
    _suppress(site, "#img", "false_positive")

    assert site.get_recent_report()["report_counts"]["violations"] == {"total": 1, "critical": 0, "serious": 0, "moderate": 1, "minor": 0}
    assert website.get_report_counts()["violations"]["total"] == 1
    assert site.to_dict()["reports"][0]["report_counts"]["violations"]["critical"] == 0


def test_partially_suppressed_rule_still_counts(app, make_user, make_website, add_site, add_report):
    website = make_website(make_user())
    site = add_site(website, page="/")
    _scan(add_report, site, [_rule("image-alt", "critical", (("#a", "<img>"), ("#b", "<img>")))])
    _suppress(site, "#a")

    assert site.get_recent_report()["report_counts"]["violations"]["critical"] == 1
    _suppress(site, "#b")
    assert site.get_recent_report()["report_counts"]["violations"]["critical"] == 0


def test_websites_ordered_by_violations_use_effective_counts(client, make_user, make_website, add_site, add_report, jwt_header):
    admin = make_user("root", is_admin=True)
    loud = make_website(admin, base="https://loud.example")
    quiet = make_website(admin, base="https://quiet.example")
    loud_home = add_site(loud, page="/")
    _scan(add_report, loud_home, [_rule("r1"), _rule("r2"), _rule("r3")])
    _scan(add_report, add_site(quiet, page="/"), [_rule("r1"), _rule("r2")])

    order = lambda: [w["url"] for w in client.get("/api/websites/?orderBy=violations", headers=jwt_header(admin)).get_json()["items"]]
    assert order() == [loud.url, quiet.url]
    for finding in loud_home.findings.all():
        set_finding_status(finding, "accepted", None, None)
    from models import db
    db.session.commit()
    assert order() == [quiet.url, loud.url]

    sites = client.get(f"/api/websites/{loud.id}/sites/", headers=jwt_header(admin)).get_json()["items"]
    assert sites[0]["current_report"]["report_counts"]["violations"]["total"] == 0


def test_dashboard_totals_rows_and_top_rules_exclude_suppressed(client, make_user, make_website, add_site, add_report, jwt_header):
    admin = make_user("root", is_admin=True)
    website = make_website(admin)
    site = add_site(website, page="/")
    _scan(add_report, site, [_rule("image-alt", "critical", (("#a", "<img>"), ("#b", "<img>"))), _rule("region", "moderate", (("#r", "<div>"),))])
    _suppress(site, "#a")

    body = client.get("/api/dashboard/", headers=jwt_header(admin)).get_json()
    assert body["totals"]["violations"]["total"] == 2  # image-alt still has an open element
    top = {r["id"]: r for r in body["top_rules"]}
    assert top["image-alt"]["occurrences"] == 1

    _suppress(site, "#b")
    body = client.get("/api/dashboard/", headers=jwt_header(admin)).get_json()
    assert body["totals"]["violations"] == {"total": 1, "critical": 0, "serious": 0, "moderate": 1, "minor": 0}
    assert body["websites"][0]["violations"]["critical"] == 0
    assert [r["id"] for r in body["top_rules"]] == ["region"]


def test_history_reflects_a_verdict_from_the_latest_point_on(client, make_user, make_website, add_site, add_report, jwt_header):
    now = datetime.now(timezone.utc)
    admin = make_user("root", is_admin=True)
    website = make_website(admin)
    site = add_site(website, page="/")
    _scan(add_report, site, [_rule("region")], when=now - timedelta(days=3))
    _scan(add_report, site, [_rule("region")], when=now)
    _suppress(site, "#a")

    points = client.get(f"/api/websites/{website.id}/history/", headers=jwt_header(admin)).get_json()["items"]
    assert [p["report_counts"]["violations"]["total"] for p in points] == [1, 0]
    site_points = client.get(f"/api/sites/{site.id}/history/", headers=jwt_header(admin)).get_json()["items"]
    assert [p["report_counts"]["violations"]["total"] for p in site_points] == [1, 0]
    dashboard = client.get("/api/dashboard/?days=30", headers=jwt_header(admin)).get_json()["history"]
    assert [p["report_counts"]["violations"]["total"] for p in dashboard] == [1, 0]

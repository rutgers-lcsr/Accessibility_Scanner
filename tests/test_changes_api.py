"""What changed between the last two scans: new, fixed, reopened and still-open findings,
the totals over pages present in both scans, and the two endpoints' visibility."""
from datetime import datetime, timedelta, timezone

import pytest

import models.website as website_models
from services.findings import changes_for_sites, refresh_suppressed_counts, sync_report_findings


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


def test_changes_new_fixed_and_still_open_after_two_scans(app, make_user, make_website, add_site, add_report):
    now = datetime.now(timezone.utc)
    website = make_website(make_user())
    home = add_site(website, page="/")
    about = add_site(website, page="/about")
    first_home = _scan(add_report, home, [_rule("region", "moderate", (("#r", "<div>"),)), _rule("color-contrast", nodes=(("#c1", "<a>1</a>"), ("#c2", "<a>2</a>")))], now - timedelta(days=7))
    _scan(add_report, about, [_rule("region", "moderate", (("#ra", "<div>"),))], now - timedelta(days=7))
    second_home = _scan(add_report, home, [_rule("region", "moderate", (("#r", "<div>"),)), _rule("image-alt", "critical", (("#img", "<img>"),))], now)
    _scan(add_report, about, [_rule("region", "moderate", (("#ra", "<div>"),))], now)

    changes = changes_for_sites([home.id, about.id])

    assert changes["since"] and changes["until"]
    assert (changes["new_count"], changes["fixed_count"], changes["open_count"], changes["reopened_count"]) == (1, 2, 3, 0)
    assert [r["rule_id"] for r in changes["new"]] == ["image-alt"]
    assert changes["new"][0]["pages"][0]["report_id"] == second_home.id
    fixed = changes["fixed"][0]
    assert fixed["rule_id"] == "color-contrast" and fixed["count"] == 2
    assert fixed["pages"][0]["report_id"] == first_home.id  # where it was last seen
    still = changes["still_open"][0]
    assert still["rule_id"] == "region" and {p["url"] for p in still["pages"]} == {home.url, about.url}
    assert changes["previous"]["total"] == 3 and changes["current"]["total"] == 3
    assert changes["regression"] is True  # a new critical finding


def test_changes_marks_a_returning_finding_as_reopened(app, make_user, make_website, add_site, add_report):
    now = datetime.now(timezone.utc)
    website = make_website(make_user())
    site = add_site(website, page="/")
    _scan(add_report, site, [_rule("region", "minor")], now - timedelta(days=14))
    _scan(add_report, site, [], now - timedelta(days=7))
    _scan(add_report, site, [_rule("region", "minor")], now)

    changes = changes_for_sites([site.id])

    assert changes["new_count"] == 1 and changes["reopened_count"] == 1
    assert changes["new"][0]["pages"][0]["findings"][0]["reopened"] is True
    assert changes["previous"]["total"] == 0 and changes["current"]["total"] == 1
    assert changes["regression"] is True  # more open violations than before


def test_changes_with_a_single_scan_have_no_baseline(app, make_user, make_website, add_site, add_report):
    website = make_website(make_user())
    site = add_site(website, page="/")
    _scan(add_report, site, [_rule("region", "critical")], datetime.now(timezone.utc))

    changes = changes_for_sites([site.id])

    assert changes["since"] is None and changes["until"]
    assert changes["new_count"] == 1 and changes["regression"] is False
    assert changes_for_sites([]) == {**changes_for_sites([]), "since": None, "regression": False}


def test_changes_endpoints_and_visibility(client, make_user, make_website, add_site, add_report, jwt_header):
    now = datetime.now(timezone.utc)
    owner = make_user("alice")
    website = make_website(owner)
    site = add_site(website, page="/")
    _scan(add_report, site, [_rule("region")], now - timedelta(days=7))
    _scan(add_report, site, [_rule("region"), _rule("label", "minor", (("#l", "<input>"),))], now)

    assert client.get(f"/api/websites/{website.id}/changes/").status_code == 403
    assert client.get(f"/api/sites/{site.id}/changes/", headers=jwt_header(make_user("carol"))).status_code == 403
    body = client.get(f"/api/websites/{website.id}/changes/", headers=jwt_header(owner)).get_json()
    assert body["new_count"] == 1 and body["new"][0]["rule_id"] == "label" and body["regression"] is True
    assert client.get(f"/api/sites/{site.id}/changes/", headers=jwt_header(owner)).get_json()["new_count"] == 1
    assert client.get("/api/websites/999/changes/", headers=jwt_header(owner)).status_code == 404

    website.public = True
    assert client.get(f"/api/websites/{website.id}/changes/").status_code == 200
    assert client.get(f"/api/sites/{site.id}/changes/").status_code == 200

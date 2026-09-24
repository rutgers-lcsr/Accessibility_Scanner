"""Triage API: who may set a verdict, what it records, that suppression drops counts at
once, bulk verdicts by rule, the listings, and the report payload."""
from datetime import datetime, timedelta, timezone

import pytest

import models.website as website_models
from models.finding import Finding
from services.findings import refresh_suppressed_counts, sync_report_findings


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setattr(website_models, "is_valid_url", lambda url: True)


def _rule(rule_id, impact="serious", nodes=(("#a", "<p>a</p>"),)):
    return {"id": rule_id, "impact": impact, "help": f"Fix {rule_id}", "helpUrl": "https://x",
            "nodes": [{"target": [s], "html": h} for s, h in nodes]}


def _scan(add_report, site, violations, when=None):
    """Store a report the way the scanner does: report row, findings, snapshot."""
    from models import db

    report = add_report(site, when=when, violations=violations)
    sync_report_findings(site.id, report.id, report.timestamp, violations)
    refresh_suppressed_counts(site.id, report.id)
    db.session.commit()
    return report


def _finding(site, selector):
    return site.findings.filter_by(selector=selector).one()


def test_verdict_requires_login_and_edit_rights(client, make_user, make_website, add_site, add_report, jwt_header):
    owner = make_user("alice")
    member = make_user("bob")
    admin = make_user("root", is_admin=True)
    website = make_website(owner)
    website.users.append(member)
    site = add_site(website, page="/")
    _scan(add_report, site, [_rule("region")])
    finding = _finding(site, "#a")

    assert client.patch(f"/api/findings/{finding.id}/", json={"status": "fixed"}).status_code == 401
    assert client.patch(f"/api/findings/{finding.id}/", json={"status": "fixed"}, headers=jwt_header(member)).status_code == 200
    assert client.patch(f"/api/findings/{finding.id}/", json={"status": "fixed"}, headers=jwt_header(owner)).status_code == 200
    assert client.patch(f"/api/findings/{finding.id}/", json={"status": "open"}, headers=jwt_header(admin)).status_code == 200
    assert client.patch("/api/findings/999/", json={"status": "open"}, headers=jwt_header(admin)).status_code == 404


def test_verdict_validates_and_records_who_and_when(client, make_user, make_website, add_site, add_report, jwt_header):
    owner = make_user("alice")
    website = make_website(owner)
    site = add_site(website, page="/")
    _scan(add_report, site, [_rule("region")])
    finding = _finding(site, "#a")

    assert client.patch(f"/api/findings/{finding.id}/", json={"status": "bogus"}, headers=jwt_header(owner)).status_code == 400
    assert client.patch(f"/api/findings/{finding.id}/", json={"status": "accepted", "note": 5}, headers=jwt_header(owner)).status_code == 400

    resp = client.patch(f"/api/findings/{finding.id}/", json={"status": "accepted", "note": "  Decorative, by design  "}, headers=jwt_header(owner))
    body = resp.get_json()
    assert body["status"] == "accepted" and body["note"] == "Decorative, by design"
    assert body["status_by"] == "alice" and body["status_at"]


def test_suppressing_a_finding_drops_the_counts_at_once(client, make_user, make_website, add_site, add_report, jwt_header):
    owner = make_user("alice")
    website = make_website(owner)
    site = add_site(website, page="/")
    _scan(add_report, site, [_rule("region", "moderate"), _rule("image-alt", "critical", (("#img", "<img>"),))])

    before = client.get(f"/api/websites/{website.id}/", headers=jwt_header(owner)).get_json()["report_counts"]["violations"]
    assert (before["total"], before["critical"]) == (2, 1)

    finding = _finding(site, "#img")
    client.patch(f"/api/findings/{finding.id}/", json={"status": "false_positive"}, headers=jwt_header(owner))

    after = client.get(f"/api/websites/{website.id}/", headers=jwt_header(owner)).get_json()["report_counts"]["violations"]
    assert (after["total"], after["critical"]) == (1, 0)
    page = client.get(f"/api/websites/{website.id}/sites/", headers=jwt_header(owner)).get_json()["items"][0]
    assert page["current_report"]["report_counts"]["violations"]["total"] == 1
    assert page["current_report"]["suppressed_counts"]["critical"] == 1


def test_bulk_verdict_touches_current_findings_of_the_rule_only(client, make_user, make_website, add_site, add_report, jwt_header):
    now = datetime.now(timezone.utc)
    owner = make_user("alice")
    website = make_website(owner)
    home = add_site(website, page="/")
    about = add_site(website, page="/about")
    _scan(add_report, home, [_rule("region", nodes=(("#old", "<p>old</p>"),))], when=now - timedelta(days=7))
    _scan(add_report, home, [_rule("region", nodes=(("#new", "<p>new</p>"),)), _rule("label")], when=now)  # #old is now fixed
    _scan(add_report, about, [_rule("region", nodes=(("#about", "<p>"),))], when=now)

    resp = client.post(f"/api/websites/{website.id}/findings/bulk/", json={"rule_id": "region", "status": "accepted", "note": "banner"}, headers=jwt_header(owner))
    assert resp.status_code == 200 and resp.get_json() == {"updated": 2}
    assert _finding(home, "#new").status == "accepted" and _finding(about, "#about").status == "accepted"
    assert _finding(home, "#old").status == "fixed"  # not current: untouched
    assert _finding(home, "#a").status == "open"  # other rule

    resp = client.post(f"/api/websites/{website.id}/findings/bulk/", json={"rule_id": "region", "status": "open", "site_id": about.id}, headers=jwt_header(owner))
    assert resp.get_json() == {"updated": 1}
    assert _finding(about, "#about").status == "open" and _finding(home, "#new").status == "accepted"

    assert client.post(f"/api/websites/{website.id}/findings/bulk/", json={"status": "open"}, headers=jwt_header(owner)).status_code == 400
    assert client.post(f"/api/websites/{website.id}/findings/bulk/", json={"rule_id": "region", "status": "open", "site_id": 999}, headers=jwt_header(owner)).status_code == 400
    assert client.post(f"/api/websites/{website.id}/findings/bulk/", json={"rule_id": "region", "status": "open"}, headers=jwt_header(make_user("carol"))).status_code == 403


def test_listings_filter_by_status_and_respect_visibility(client, make_user, make_website, add_site, add_report, jwt_header):
    now = datetime.now(timezone.utc)
    owner = make_user("alice")
    website = make_website(owner)
    site = add_site(website, page="/")
    _scan(add_report, site, [_rule("region", nodes=(("#gone", "<p>gone</p>"),))], when=now - timedelta(days=7))
    _scan(add_report, site, [_rule("region", nodes=(("#here", "<p>here</p>"),)), _rule("image-alt", "critical", (("#img", "<img>"),))], when=now)
    _finding(site, "#img").status = "accepted"

    url = f"/api/websites/{website.id}/findings/"
    assert client.get(url).status_code == 403  # private, anonymous
    assert client.get(url, headers=jwt_header(make_user("carol"))).status_code == 403

    current = client.get(url, headers=jwt_header(owner)).get_json()
    assert current["count"] == 2 and [r["rule_id"] for r in current["rules"]] == ["image-alt", "region"]
    assert current["rules"][1]["counts"]["open"] == 1 and current["rules"][1]["pages"][0]["url"] == site.url
    assert client.get(url + "?status=fixed", headers=jwt_header(owner)).get_json()["rules"][0]["pages"][0]["findings"][0]["selector"] == "#gone"
    assert client.get(url + "?status=suppressed", headers=jwt_header(owner)).get_json()["count"] == 1
    assert client.get(url + "?status=all", headers=jwt_header(owner)).get_json()["count"] == 3
    assert client.get(url + "?rule=region", headers=jwt_header(owner)).get_json()["count"] == 1
    assert client.get(url + "?status=nope", headers=jwt_header(owner)).status_code == 400

    site_url = f"/api/sites/{site.id}/findings/"
    assert client.get(site_url, headers=jwt_header(owner)).get_json()["count"] == 2

    website.public = True
    assert client.get(url).status_code == 200 and client.get(site_url).status_code == 200


def test_report_payload_carries_findings_for_the_latest_report_only(client, make_user, make_website, add_site, add_report, jwt_header):
    now = datetime.now(timezone.utc)
    owner = make_user("alice")
    website = make_website(owner)
    site = add_site(website, page="/")
    older = _scan(add_report, site, [_rule("region")], when=now - timedelta(days=7))
    latest = _scan(add_report, site, [_rule("region")], when=now)

    body = client.get(f"/api/reports/{latest.id}/", headers=jwt_header(owner)).get_json()
    assert [f["selector"] for f in body["findings"]] == ["#a"] and body["can_edit"] is True
    assert body["suppressed_counts"]["total"] == 0
    assert client.get(f"/api/reports/{older.id}/", headers=jwt_header(owner)).get_json()["findings"] is None
    assert client.get(f"/api/reports/{latest.id}/", headers=jwt_header(make_user("root", is_admin=True))).get_json()["can_edit"] is True
    website.public = True
    assert client.get(f"/api/reports/{latest.id}/").get_json()["can_edit"] is False

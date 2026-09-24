"""Members (the users a website admin adds) triage findings, edit the member list and
start pages and see the report page's actions; strangers and anonymous callers cannot."""
import pytest

import blueprints.website as website_bp
import models.website as website_models
from models import db
from services.findings import refresh_suppressed_counts, sync_report_findings


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setattr(website_models, "is_valid_url", lambda url: True)
    monkeypatch.setattr(website_bp, "is_valid_url", lambda url: True)


def _rule(rule_id, impact="serious", selector="#a"):
    return {"id": rule_id, "impact": impact, "help": f"Fix {rule_id}", "helpUrl": "https://x",
            "nodes": [{"target": [selector], "html": f"<p>{selector}</p>"}]}


def _scan(add_report, site, violations):
    report = add_report(site, violations=violations)
    sync_report_findings(site.id, report.id, report.timestamp, violations)
    refresh_suppressed_counts(site.id, report.id)
    db.session.commit()
    return report


def _finding(site, selector):
    return site.findings.filter_by(selector=selector).one()


def _setup(make_user, make_website, add_site, add_report):
    owner = make_user("alice")
    member = make_user("bob")
    website = make_website(owner, base="https://example.com")
    website.users.append(member)
    db.session.commit()
    site = add_site(website, page="/")
    report = _scan(add_report, site, [_rule("region", selector="#a"), _rule("label", "critical", "#l")])
    return owner, member, website, site, report


def test_members_can_triage_edit_membership_and_start_pages(client, make_user, make_website, add_site, add_report, jwt_header):
    owner, member, website, site, report = _setup(make_user, make_website, add_site, add_report)
    headers = jwt_header(member)

    assert client.patch(f"/api/findings/{_finding(site, '#a').id}/", json={"status": "fixed"}, headers=headers).status_code == 200
    assert client.post(f"/api/websites/{website.id}/findings/bulk/", json={"rule_id": "label", "status": "accepted"}, headers=headers).status_code == 200
    assert _finding(site, "#l").status == "accepted"

    resp = client.patch(f"/api/websites/{website.id}/", json={"users": ["bob"], "extra_start_urls": ["https://example.com/section/"]}, headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()["extra_start_urls"] == ["https://example.com/section/"]

    # site-admin-only fields are ignored, not refused
    resp = client.patch(f"/api/websites/{website.id}/", json={"public": True}, headers=headers)
    assert resp.status_code == 200
    db.session.refresh(website)
    assert website.public is False

    assert client.get(f"/api/reports/{report.id}/", headers=headers).get_json()["can_edit"] is True
    assert site.can_edit(member) is True and website.can_scan(member) is True


def test_strangers_and_anonymous_still_cannot(client, make_user, make_website, add_site, add_report, jwt_header):
    owner, member, website, site, report = _setup(make_user, make_website, add_site, add_report)
    website.public = True
    db.session.commit()
    finding_id = _finding(site, "#a").id
    stranger = jwt_header(make_user("carol"))

    assert client.patch(f"/api/findings/{finding_id}/", json={"status": "fixed"}).status_code == 401
    assert client.patch(f"/api/findings/{finding_id}/", json={"status": "fixed"}, headers=stranger).status_code == 403
    assert client.post(f"/api/websites/{website.id}/findings/bulk/", json={"rule_id": "label", "status": "accepted"}, headers=stranger).status_code == 403
    assert client.patch(f"/api/websites/{website.id}/", json={"users": ["carol"]}, headers=stranger).status_code == 403
    assert client.get(f"/api/reports/{report.id}/").get_json()["can_edit"] is False
    assert client.get(f"/api/reports/{report.id}/", headers=stranger).get_json()["can_edit"] is False

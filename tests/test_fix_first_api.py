"""GET /api/websites/<id>/fix-first/: the open violations as rules ranked by the pages a
fix clears, with one example element per rule and whether a guide exists."""
import pytest

import models.website as website_models
from models import db
from services.findings import refresh_suppressed_counts, set_finding_status, sync_report_findings


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setattr(website_models, "is_valid_url", lambda url: True)


def _rule(rule_id, impact="serious", nodes=(("#a", "<p>a</p>"),), summary=None):
    return {"id": rule_id, "impact": impact, "help": f"Fix {rule_id}", "helpUrl": f"https://x/{rule_id}",
            "nodes": [{"target": [selector], "html": html, "failureSummary": summary or f"Fix {rule_id} at {selector}"}
                      for selector, html in nodes]}


def _scan(add_report, site, violations):
    report = add_report(site, violations=violations)
    sync_report_findings(site.id, report.id, report.timestamp, violations)
    refresh_suppressed_counts(site.id, report.id)
    db.session.commit()
    return report


def _finding(site, selector):
    return site.findings.filter_by(selector=selector).one()


def _fix_first(client, headers, website):
    resp = client.get(f"/api/websites/{website.id}/fix-first/", headers=headers)
    assert resp.status_code == 200
    return resp.get_json()


def test_fix_first_ranks_by_pages_cleared_then_impact_then_id(client, make_user, make_website, add_site, add_report, jwt_header):
    owner = make_user("alice")
    website = make_website(owner)
    one, two, three = (add_site(website, page=f"/{n}") for n in ("one", "two", "three"))
    images = _rule("image-alt", "critical", nodes=(("#i1", "<img>"), ("#i2", "<img>"), ("#i3", "<img>")))
    label = _rule("label", "critical", nodes=(("#l", "<input>"),))
    _scan(add_report, one, [_rule("region", "moderate"), images, label])
    _scan(add_report, two, [_rule("region", "moderate"), _rule("image-alt", "critical", nodes=(("#i1", "<img>"),)), label])
    _scan(add_report, three, [_rule("region", "moderate")])

    data = _fix_first(client, jwt_header(owner), website)

    assert (data["pages_total"], data["pages_audited"], data["open_total"], data["suppressed_rules"]) == (3, 3, 9, 0)
    rules = data["rules"]
    assert [r["rule_id"] for r in rules] == ["region", "image-alt", "label"]
    assert [r["pages_affected"] for r in rules] == [3, 2, 2]
    assert [r["pages_cleared_percent"] for r in rules] == [100, 67, 67]
    assert [r["elements"] for r in rules] == [3, 4, 2]
    image_alt = rules[1]
    assert image_alt["pages"][0] == {"site_id": one.id, "url": one.url, "report_id": image_alt["pages"][0]["report_id"], "count": 3}
    assert image_alt["pages"][1]["count"] == 1
    assert image_alt["example"]["url"] == one.url and image_alt["example"]["selector"] == "#i1"
    assert image_alt["counts"] == {"open": 4, "fixed": 0, "false_positive": 0, "accepted": 0}


def test_fix_first_counts_open_current_findings_only(client, make_user, make_website, add_site, add_report, jwt_header):
    owner = make_user("alice")
    website = make_website(owner)
    one = add_site(website, page="/one")
    two = add_site(website, page="/two")
    add_site(website, page="/never-scanned")
    _scan(add_report, one, [_rule("region"), _rule("list", nodes=(("#ul", "<ul>"),))])
    _scan(add_report, two, [_rule("region")])
    assert _fix_first(client, jwt_header(owner), website)["rules"][0]["pages_affected"] == 2

    set_finding_status(_finding(one, "#a"), "accepted", None, owner.id)
    set_finding_status(_finding(one, "#ul"), "accepted", None, owner.id)
    db.session.commit()

    data = _fix_first(client, jwt_header(owner), website)
    assert (data["pages_total"], data["pages_audited"], data["open_total"], data["suppressed_rules"]) == (3, 2, 1, 1)
    assert [r["rule_id"] for r in data["rules"]] == ["region"]
    region = data["rules"][0]
    assert region["pages_affected"] == 1 and region["pages"][0]["url"] == two.url
    assert region["counts"] == {"open": 1, "fixed": 0, "false_positive": 0, "accepted": 1}

    _scan(add_report, two, [])  # the scanner closes region on page two: no open page is left

    data = _fix_first(client, jwt_header(owner), website)
    assert data["rules"] == [] and data["open_total"] == 0 and data["suppressed_rules"] == 2


def test_fix_first_example_and_guide_flag(client, make_user, make_website, add_site, add_report, jwt_header):
    owner = make_user("alice")
    website = make_website(owner)
    site = add_site(website, page="/")
    report = _scan(add_report, site, [
        _rule("region", "moderate", nodes=(("#a", '<div class="a">a</div>'),), summary="Some page content is not contained by landmarks"),
        _rule("label", "critical", nodes=(("#l", "<input>"),)),
    ])

    rules = {r["rule_id"]: r for r in _fix_first(client, jwt_header(owner), website)["rules"]}

    assert rules["region"]["example"] == {
        "finding_id": _finding(site, "#a").id, "site_id": site.id, "url": site.url, "report_id": report.id,
        "selector": "#a", "html": '<div class="a">a</div>',
        "failure_summary": "Some page content is not contained by landmarks",
    }
    assert rules["region"]["guide"] is True
    assert rules["label"]["guide"] is False


def test_fix_first_visibility(client, make_user, make_website, add_site, add_report, jwt_header):
    owner = make_user("alice")
    member = make_user("bob")
    website = make_website(owner)
    website.users.append(member)
    db.session.commit()
    _scan(add_report, add_site(website, page="/"), [_rule("region")])
    url = f"/api/websites/{website.id}/fix-first/"

    assert client.get("/api/websites/999/fix-first/", headers=jwt_header(owner)).status_code == 404
    assert client.get(url).status_code == 403
    assert client.get(url, headers=jwt_header(make_user("carol"))).status_code == 403
    assert client.get(url, headers=jwt_header(member)).status_code == 200

    website.public = True
    db.session.commit()
    assert client.get(url).status_code == 200

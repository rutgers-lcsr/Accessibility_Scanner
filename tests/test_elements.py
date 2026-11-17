"""Every current failing element of a website, grouped by the markup they share, for a
developer's to-do list and download (CSV or JSON)."""
from models import db
from services.elements import signature
from services.findings import refresh_suppressed_counts, sync_report_findings

SUMMARY = ("Fix any of the following:\n  Element has insufficient color contrast of 2.68 "
           "(foreground color: #39adb5, background color: #ffffff, font size: 8.9pt (11.9px), "
           "font weight: normal). Expected contrast ratio of 4.5:1")


def _scan(add_report, site, nodes, rule_id="color-contrast"):
    violations = [{"id": rule_id, "impact": "serious", "help": "Contrast", "helpUrl": "https://x",
                   "nodes": [{"target": [s], "html": h, "failureSummary": SUMMARY} for s, h in nodes]}]
    report = add_report(site, violations=violations)
    sync_report_findings(site.id, report.id, report.timestamp, violations)
    refresh_suppressed_counts(site.id, report.id)
    db.session.commit()
    return report


def test_signature_ignores_position_and_keeps_classes_and_colours():
    a = signature('color-contrast', '<span class="token decorator annotation" style="color: rgb(57, 173, 181);">@test</span>', SUMMARY)
    b = signature('color-contrast', '<span class="annotation token decorator">@other</span>', SUMMARY)
    assert a == b
    assert a['label'] == '<span class="annotation decorator token"> · #39adb5 on #ffffff'
    other = signature('color-contrast', '<div class="note">x</div>', SUMMARY)
    assert other['key'] != a['key']


def test_elements_endpoint_groups_and_downloads(client, make_user, make_website, add_site, add_report, jwt_header):
    owner = make_user("alice")
    website = make_website(owner)
    guide = add_site(website, page="/guide")
    demo = add_site(website, page="/demo")
    _scan(add_report, guide, [(f"span:nth-child({i})", f'<span class="token decorator">@t{i}</span>') for i in range(3)])
    _scan(add_report, demo, [("span.x", '<span class="token decorator">@d</span>'), ("p.note", '<p class="note">n</p>')])
    headers = jwt_header(owner)

    body = client.get(f"/api/websites/{website.id}/elements/?rule=color-contrast", headers=headers).get_json()
    assert body["count"] == 5
    first = body["groups"][0]
    assert first["count"] == 4 and first["pages"] == 2
    assert {e["url"] for e in first["elements"]} == {guide.url, demo.url}
    assert body["groups"][1]["count"] == 1

    resp = client.get(f"/api/websites/{website.id}/elements/?rule=color-contrast&format=csv", headers=headers)
    assert resp.status_code == 200 and resp.mimetype == "text/csv"
    lines = resp.get_data(as_text=True).strip().splitlines()
    assert lines[0].startswith("id,rule,impact,group,page,selector")
    assert len(lines) == 6

    assert client.get(f"/api/websites/{website.id}/elements/", headers=jwt_header(make_user("carol"))).status_code == 403


def test_signature_ignores_generated_css_classes():
    a = signature('color-contrast', '<span class="ant-typography css-var-_r_0_ css-viwxw0">a</span>', None)
    b = signature('color-contrast', '<span class="ant-typography css-dev-only-abc css-1q2w3e">b</span>', None)
    assert a == b and a['label'] == '<span class="ant-typography">'


def test_status_for_a_group_of_elements(client, make_user, make_website, add_site, add_report, jwt_header, monkeypatch):
    """A developer marks one group (one template) at a time: the ids must be current
    findings of this website, and suppressing still needs a reason."""
    import models.website as website_models
    monkeypatch.setattr(website_models, "is_valid_url", lambda url: True)
    owner = make_user("alice")
    website = make_website(owner)
    site = add_site(website, page="/guide")
    _scan(add_report, site, [("span.a", '<span class="token">a</span>'), ("span.b", '<span class="token">b</span>'), ("p.c", '<p>c</p>')])
    other = make_website(make_user("bob"), base="https://other.example")
    other_site = add_site(other, page="/x")
    _scan(add_report, other_site, [("span.z", '<span class="token">z</span>')])
    ids = [f.id for f in site.findings.all() if f.selector in ("span.a", "span.b")]
    foreign = other_site.findings.first().id
    url = f"/api/websites/{website.id}/findings/bulk-ids/"
    headers = jwt_header(owner)

    assert client.post(url, json={"ids": ids, "status": "accepted"}, headers=headers).status_code == 400
    assert client.post(url, json={"ids": ids + [foreign], "status": "fixed"}, headers=headers).status_code == 400
    assert client.post(url, json={"ids": ids, "status": "fixed"}, headers=jwt_header(make_user("carol"))).status_code == 403

    resp = client.post(url, json={"ids": ids, "status": "false_positive", "note": "Code theme colours, vendor plugin"}, headers=headers)
    assert resp.status_code == 200 and resp.get_json()["updated"] == 2
    statuses = {f.selector: f.status for f in site.findings.all()}
    assert statuses == {"span.a": "false_positive", "span.b": "false_positive", "p.c": "open"}

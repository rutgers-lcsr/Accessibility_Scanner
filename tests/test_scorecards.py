"""Department scorecards and the compliance report."""
import csv
import io
from datetime import datetime, timedelta

import pytest

import models.website as website_models
from models import db
from models.compliance import ManualReview
from models.finding import Finding
from models.health import HealthCheck, WebsiteHealth
from services.findings import sync_report_findings
from services.scorecards import REPORT_COLUMNS, UNASSIGNED, compliance_rows, department_scorecards


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setattr(website_models, "is_valid_url", lambda url: True)


def _violation(rule, impact):
    return {"id": rule, "impact": impact, "help": "h", "helpUrl": "u",
            "nodes": [{"target": [f"#{rule}"], "html": "<p>x</p>"}]}


def _setup(make_user, make_website, add_site, add_report):
    """CS: one website with a critical issue overdue and a fixed one; Math: one clean
    website; one website without a department; one retired CS website."""
    owner = make_user("owner")
    now = datetime.utcnow()
    cs = make_website(owner, base="https://cs.example")
    cs.department = "CS"
    page = add_site(cs, "/")
    report = add_report(page, violations=[_violation("image-alt", "critical")])
    sync_report_findings(page.id, report.id, report.timestamp, report.report["violations"])
    db.session.query(Finding).update({"first_seen": now - timedelta(days=100)})
    db.session.add(Finding(site_id=page.id, rule_id="label", fingerprint="f" * 40, impact="serious",
                           first_seen=now - timedelta(days=20), last_seen=now - timedelta(days=10),
                           status="fixed", status_at=now - timedelta(days=10)))
    cs.last_scanned = now
    db.session.add(WebsiteHealth(website_id=cs.id, checked_at=now, up=True, tls_valid=False,
                                 security_headers={"Strict-Transport-Security": "max-age=1"}))
    db.session.add_all([HealthCheck(website_id=cs.id, checked_at=now - timedelta(hours=h), up=h != 1) for h in range(1, 5)])

    math = make_website(owner, base="https://math.example")
    math.department = "Math"
    math_page = add_site(math, "/")
    add_report(math_page, violations=[])
    math.last_scanned = now
    db.session.add(ManualReview(website_id=math.id, status="completed", started_at=now, completed_at=now))

    nobody = make_website(owner, base="https://nobody.example")
    retired = make_website(owner, base="https://old.cs.example")
    retired.department, retired.lifecycle_status = "CS", "retired"
    db.session.commit()
    return owner, cs, math, nobody, retired


def test_compliance_rows(app, make_user, make_website, add_site, add_report):
    _, cs, math, nobody, retired = _setup(make_user, make_website, add_site, add_report)
    rows = {row["url"]: row for row in compliance_rows([cs, math, nobody, retired])}
    row = rows[cs.url]
    assert row["critical"] == 1 and row["overdue"] == 1
    assert row["median_days_to_fix"] == 10.0
    assert row["uptime_30d"] == 75.0 and row["tls_valid"] is False and row["security_headers"] == 1
    assert row["review_due"] is True
    assert rows[math.url]["review_due"] is False and rows[math.url]["critical"] == 0
    assert rows[nobody.url]["department"] is None and rows[nobody.url]["up"] is None


def test_department_scorecards(app, make_user, make_website, add_site, add_report):
    _, cs, math, nobody, retired = _setup(make_user, make_website, add_site, add_report)
    cards = department_scorecards(compliance_rows([cs, math, nobody, retired]))
    assert [card["department"] for card in cards] == ["CS", "Math", UNASSIGNED]  # worst first, retired left out
    by_name = {card["department"]: card for card in cards}
    assert by_name["CS"]["websites"] == 1 and by_name["CS"]["overdue"] == 1 and by_name["CS"]["tls_problems"] == 1
    assert by_name["CS"]["clean_percent"] == 0.0 and by_name["Math"]["clean_percent"] == 100.0
    assert by_name["Math"]["reviewed_percent"] == 100.0
    assert by_name[UNASSIGNED]["audited"] == 0 and by_name[UNASSIGNED]["clean_percent"] is None


def test_scorecards_endpoint_respects_visibility(client, jwt_header, make_user, make_website, add_site, add_report):
    owner, cs, *_ = _setup(make_user, make_website, add_site, add_report)
    stranger = make_user("stranger")
    mine = make_website(stranger, base="https://stranger.example")
    mine.department = "Physics"
    db.session.commit()

    body = client.get("/api/scorecards/", headers=jwt_header(stranger)).get_json()
    assert [card["department"] for card in body["departments"]] == ["Physics"]
    admin = make_user("root", is_admin=True)
    body = client.get("/api/scorecards/", headers=jwt_header(admin)).get_json()
    assert {card["department"] for card in body["departments"]} == {"CS", "Math", "Physics", UNASSIGNED}
    assert body["totals"]["websites"] == 4
    assert client.get("/api/scorecards/").status_code == 401


def test_compliance_report_json_and_csv(client, jwt_header, make_user, make_website, add_site, add_report):
    owner, cs, math, nobody, retired = _setup(make_user, make_website, add_site, add_report)
    headers = jwt_header(owner)

    body = client.get("/api/compliance-report/?department=CS", headers=headers).get_json()
    assert [row["url"] for row in body["websites"]] == [cs.url]
    assert body["summary"]["overdue"] == 1 and "fix_days" not in body["websites"][0]
    body = client.get("/api/compliance-report/?department=CS&include_retired=true", headers=headers).get_json()
    assert sorted(row["url"] for row in body["websites"]) == [cs.url, retired.url]
    body = client.get(f"/api/compliance-report/?department={UNASSIGNED}", headers=headers).get_json()
    assert [row["url"] for row in body["websites"]] == [nobody.url]

    resp = client.get("/api/compliance-report/?format=csv", headers=headers)
    assert resp.mimetype == "text/csv" and "attachment" in resp.headers["Content-Disposition"]
    table = list(csv.reader(io.StringIO(resp.get_data(as_text=True))))
    assert table[0] == list(REPORT_COLUMNS)
    assert len(table) == 4  # header + three websites that are not retired

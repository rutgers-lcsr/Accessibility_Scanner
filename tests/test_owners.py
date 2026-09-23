"""The admin Owners overview (GET /api/dashboard/owners/): websites grouped by their
admin user, worst first, with each owner's contact details, the change since the last
email and since the period start, how many findings a person triaged, and the CSV."""
import csv
import io
from datetime import datetime, timedelta, timezone

import pytest

import models.website as website_models
from blueprints.dashboard import OWNER_CSV_COLUMNS
from models import db
from services.findings import refresh_suppressed_counts, set_finding_status, sync_report_findings


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setattr(website_models, "is_valid_url", lambda url: True)


def _rule(rule_id, impact="serious", selector="#a"):
    return {"id": rule_id, "impact": impact, "help": f"Fix {rule_id}", "helpUrl": "https://x",
            "nodes": [{"target": [selector], "html": f"<p>{selector}</p>"}]}


def _scan(add_report, site, violations, when=None):
    """Store a report the way the scanner does: report row, findings, snapshot."""
    report = add_report(site, when=when, violations=violations)
    sync_report_findings(site.id, report.id, report.timestamp, violations)
    refresh_suppressed_counts(site.id, report.id)
    db.session.commit()
    return report


def _finding(site, selector):
    return site.findings.filter_by(selector=selector).one()


def _owners(client, headers, query=""):
    resp = client.get(f"/api/dashboard/owners/{query}", headers=headers)
    assert resp.status_code == 200
    return resp.get_json()["owners"]


def test_owners_requires_a_site_admin(client, make_user, make_website, jwt_header):
    owner = make_user("alice")
    admin = make_user("root", is_admin=True)
    make_website(owner)

    assert client.get("/api/dashboard/owners/").status_code == 401
    assert client.get("/api/dashboard/owners/", headers=jwt_header(owner)).status_code == 403
    assert client.get("/api/dashboard/owners/", headers=jwt_header(admin)).status_code == 200


def test_owners_groups_websites_by_admin_worst_first(client, make_user, make_website, add_site, add_report, jwt_header):
    admin = make_user("root", is_admin=True)
    alice = make_user("alice")
    bob = make_user("bob")
    a1 = make_website(alice, base="https://a1.example.com")
    b1 = make_website(bob, base="https://b1.example.com")
    b2 = make_website(bob, base="https://b2.example.com")
    orphan = make_website(alice, base="https://orphan.example.com")
    orphan.admin_id = None
    b1.description = "Bob's lab"
    b1.users.append(alice)
    b1.last_scanned = datetime(2026, 9, 1, 12, 0)
    b2.last_scanned = datetime(2026, 8, 1, 12, 0)
    db.session.commit()
    _scan(add_report, add_site(a1), [_rule("r1", "critical")])
    _scan(add_report, add_site(b1), [_rule("r1"), _rule("r2", "minor", "#b")])
    _scan(add_report, add_site(b2), [_rule("r1")])
    _scan(add_report, add_site(orphan), [])

    owners = _owners(client, jwt_header(admin))

    assert [o["username"] for o in owners] == ["bob", "alice", None]
    bob_row = owners[0]
    assert bob_row["id"] == bob.id and bob_row["email"] == "bob@rutgers.edu"
    assert (bob_row["websites_count"], bob_row["pages"], bob_row["pages_audited"]) == (2, 2, 2)
    assert (bob_row["violations"]["total"], bob_row["violations"]["serious"], bob_row["violations"]["minor"]) == (3, 2, 1)
    assert [w["url"] for w in bob_row["websites"]] == ["https://b1.example.com", "https://b2.example.com"]
    assert bob_row["websites"][0]["description"] == "Bob's lab"
    assert bob_row["websites"][0]["users"] == ["alice"]
    assert bob_row["last_scanned"] == "2026-09-01T12:00:00Z" and bob_row["last_notified"] is None
    unassigned = owners[2]
    assert unassigned["id"] is None and unassigned["email"] is None
    assert [w["url"] for w in unassigned["websites"]] == ["https://orphan.example.com"]


def test_owners_activity_counts_only_verdicts_people_gave(client, make_user, make_website, add_site, add_report, jwt_header):
    admin = make_user("root", is_admin=True)
    alice = make_user("alice")
    website = make_website(alice)
    site = add_site(website)
    _scan(add_report, site, [_rule("r1", selector="#a"), _rule("r2", selector="#b"), _rule("r3", selector="#c")])

    # alice accepts #a through the API and the site admin marks #b fixed by hand ...
    resp = client.patch(f"/api/findings/{_finding(site, '#a').id}/", json={"status": "accepted"}, headers=jwt_header(alice))
    assert resp.status_code == 200
    set_finding_status(_finding(site, "#b"), "fixed", None, admin.id)
    db.session.commit()
    # ... the scanner closes #c on the next scan, and a person reopening it is no verdict either
    _scan(add_report, site, [_rule("r1", selector="#a")])
    assert _finding(site, "#c").status == "fixed" and _finding(site, "#c").status_by is None
    set_finding_status(_finding(site, "#c"), "open", None, alice.id)
    db.session.commit()

    owner = _owners(client, jwt_header(admin))[0]
    website_row = owner["websites"][0]
    assert website_row["activity"]["triaged"] == 2
    latest = max(_finding(site, "#a").status_at, _finding(site, "#b").status_at)
    assert website_row["activity"]["last_triage"] == latest.strftime("%Y-%m-%dT%H:%M:%SZ")
    assert owner["activity"] == website_row["activity"]


def test_owners_change_since_last_email_and_since_the_period_start(client, make_user, make_website, add_site, add_report, jwt_header):
    now = datetime.now(timezone.utc)
    admin = make_user("root", is_admin=True)
    alice = make_user("alice")
    website = make_website(alice)
    site = add_site(website)
    rules = [_rule("r1", selector="#a"), _rule("r2", selector="#b"), _rule("r3", selector="#c")]
    _scan(add_report, site, rules, when=now - timedelta(days=100))
    _scan(add_report, site, rules[:2], when=now - timedelta(days=10))
    _scan(add_report, site, rules[:1], when=now)
    website.last_notified = (now - timedelta(days=5)).replace(tzinfo=None)
    fresh = make_website(alice, base="https://fresh.example.com")
    _scan(add_report, add_site(fresh), [_rule("r1")])

    owner = _owners(client, jwt_header(admin), "?days=90")[0]

    rows = {w["url"]: w for w in owner["websites"]}
    old = rows["https://example.com"]
    assert (old["since_last_email"]["previous"], old["since_last_email"]["current"]) == (2, 1)
    assert old["since_last_email"]["when"] == old["last_notified"]
    assert old["since_period"] == {"previous": 3, "current": 1}
    assert rows["https://fresh.example.com"]["since_last_email"] is None
    assert rows["https://fresh.example.com"]["since_period"] is None
    # owner sums cover only the websites that have that baseline
    assert owner["since_last_email"] == {"previous": 2, "current": 1}
    assert owner["since_period"] == {"previous": 3, "current": 1}
    assert owner["violations"]["total"] == 2


def test_owners_counts_leave_out_suppressed_rules(client, make_user, make_website, add_site, add_report, jwt_header):
    admin = make_user("root", is_admin=True)
    alice = make_user("alice")
    website = make_website(alice)
    site = add_site(website)
    _scan(add_report, site, [_rule("r1", selector="#a"), _rule("r2", selector="#b")])
    assert _owners(client, jwt_header(admin))[0]["violations"]["total"] == 2

    set_finding_status(_finding(site, "#a"), "accepted", None, alice.id)
    db.session.commit()

    owner = _owners(client, jwt_header(admin))[0]
    assert owner["violations"]["total"] == 1
    assert owner["websites"][0]["violations"]["total"] == 1


def test_owners_csv_has_one_row_per_website_and_quotes_descriptions(client, make_user, make_website, add_site, add_report, jwt_header):
    admin = make_user("root", is_admin=True)
    alice = make_user("alice")
    website = make_website(alice)
    website.description = 'Lab, "main" site\nsecond line'
    website.categories = "labs,cs"
    db.session.commit()
    _scan(add_report, add_site(website), [_rule("r1", "critical")])

    resp = client.get("/api/dashboard/owners/?format=csv", headers=jwt_header(admin))

    assert resp.status_code == 200 and resp.mimetype == "text/csv"
    rows = list(csv.reader(io.StringIO(resp.get_data(as_text=True))))
    assert rows[0] == OWNER_CSV_COLUMNS
    assert len(rows) == 2
    row = dict(zip(rows[0], rows[1]))
    assert row["owner"] == "alice" and row["owner_email"] == "alice@rutgers.edu"
    assert row["description"] == 'Lab, "main" site\nsecond line'
    assert row["categories"] == "labs, cs"
    assert (row["violations"], row["critical"], row["violations_at_last_email"]) == ("1", "1", "")

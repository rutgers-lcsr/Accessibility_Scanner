"""System-wide dashboard: visibility scoping, latest-report-per-page totals, rankings,
categories, top violations and daily history."""
from datetime import datetime, timedelta, timezone

import pytest

import models.website as website_models
from services.history import daily_history


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setattr(website_models, "is_valid_url", lambda url: True)


def _rule(rule_id, impact, nodes=1):
    return {
        "id": rule_id,
        "impact": impact,
        "description": f"{rule_id} description",
        "help": f"Fix {rule_id}",
        "helpUrl": f"https://example.com/rules/{rule_id}",
        "nodes": [{"target": [f"#{i}"], "html": "<div>", "failureSummary": "fix it"} for i in range(nodes)],
    }


def _now():
    return datetime.now(timezone.utc)


def _seed(make_user, make_website, add_site, add_report):
    """Two websites owned by bob: A (private, 2 pages, 2 scans of the home page) and
    B (public, 1 page). Returns (owner, a, b)."""
    from models import db

    owner = make_user("bob")
    now = _now()

    a = make_website(owner, base="https://a.example")
    a.categories = "labs, teaching"
    a.last_scan_status = "completed"
    a.last_scanned = now
    a_home = add_site(a, page="/")
    a_about = add_site(a, page="/about")
    add_report(a_home, when=now - timedelta(days=3),
               violations=[_rule("color-contrast", "serious", 5), _rule("image-alt", "critical", 2)])
    add_report(a_home, when=now, violations=[_rule("color-contrast", "serious", 1)])  # older issues fixed
    add_report(a_about, when=now - timedelta(days=1),
               violations=[_rule("color-contrast", "serious", 2), _rule("label", "critical", 1)])

    b = make_website(owner, base="https://b.example", public=True)
    b.last_scan_status = "unreachable"
    b.last_scanned = now
    add_report(add_site(b, page="/"), when=now, violations=[_rule("image-alt", "critical", 4)])
    db.session.commit()
    return owner, a, b


def test_dashboard_requires_login(client):
    assert client.get("/api/dashboard/").status_code == 401


def test_dashboard_is_empty_for_a_user_without_websites(client, make_user, jwt_header):
    body = client.get("/api/dashboard/", headers=jwt_header(make_user())).get_json()
    assert body["totals"]["websites"] == 0
    assert body["totals"]["violations"]["total"] == 0
    assert body["websites"] == [] and body["categories"] == [] and body["top_rules"] == [] and body["history"] == []


def test_dashboard_aggregates_the_latest_report_of_every_page(
    client, make_user, make_website, add_site, add_report, jwt_header
):
    admin = make_user("root", is_admin=True)
    _seed(make_user, make_website, add_site, add_report)

    body = client.get("/api/dashboard/", headers=jwt_header(admin)).get_json()

    totals = body["totals"]
    assert totals["websites"] == 2
    assert totals["pages"] == 3 and totals["pages_audited"] == 3
    # latest per page: A/ -> 1 serious; A/about -> 1 serious + 1 critical; B/ -> 1 critical
    assert totals["violations"]["critical"] == 2
    assert totals["violations"]["serious"] == 2
    assert totals["violations"]["total"] == 4
    assert totals["scan_status"] == {"completed": 1, "unreachable": 1}
    assert totals["last_scan"]

    rows = {row["url"]: row for row in body["websites"]}
    assert rows["https://a.example"]["violations"]["total"] == 3
    assert rows["https://a.example"]["pages"] == 2 and rows["https://a.example"]["pages_audited"] == 2
    assert rows["https://a.example"]["categories"] == ["labs", "teaching"]
    assert rows["https://a.example"]["last_scan_status"] == "completed"
    assert rows["https://b.example"]["violations"]["critical"] == 1
    assert body["websites"][0]["url"] == "https://a.example"  # most violations first

    categories = {c["category"]: c for c in body["categories"]}
    assert categories["labs"]["websites"] == 1 and categories["labs"]["violations"]["total"] == 3
    assert categories["Uncategorized"]["websites"] == 1 and categories["Uncategorized"]["pages"] == 1

    top = {rule["id"]: rule for rule in body["top_rules"]}
    assert top["color-contrast"]["pages"] == 2 and top["color-contrast"]["occurrences"] == 3
    assert top["image-alt"]["pages"] == 1 and top["image-alt"]["occurrences"] == 4  # only B's latest counts
    assert top["label"]["help_url"] == "https://example.com/rules/label"
    assert body["top_rules"][0]["impact"] == "critical"  # most severe first
    assert [r["id"] for r in body["top_rules"]][:2] == ["image-alt", "label"]  # then pages, then occurrences

    assert [point["date"] for point in body["history"]] == sorted(point["date"] for point in body["history"])
    assert len(body["history"]) == 3  # three distinct scan days
    assert body["history"][-1]["report_counts"]["violations"]["total"] == 4


def test_dashboard_is_scoped_by_visibility(client, make_user, make_website, add_site, add_report, jwt_header):
    from models import db

    owner, a, b = _seed(make_user, make_website, add_site, add_report)
    other = make_user("alice")
    member = make_user("carol")
    a.users.append(member)
    db.session.commit()

    def urls(user):
        body = client.get("/api/dashboard/", headers=jwt_header(user)).get_json()
        return sorted(row["url"] for row in body["websites"]), body["totals"]["violations"]["total"]

    assert urls(other) == (["https://b.example"], 1)  # public only
    assert urls(member) == (["https://a.example", "https://b.example"], 4)
    assert urls(owner) == (["https://a.example", "https://b.example"], 4)


def test_dashboard_history_window_and_limits(client, make_user, make_website, add_site, add_report, jwt_header):
    owner, _, _ = _seed(make_user, make_website, add_site, add_report)

    body = client.get("/api/dashboard/?days=2&top=1", headers=jwt_header(owner)).get_json()
    assert body["days"] == 2
    assert len(body["history"]) == 2  # the scan three days ago falls outside the window
    assert len(body["top_rules"]) == 1

    body = client.get("/api/dashboard/?days=1000&top=999", headers=jwt_header(owner)).get_json()
    assert body["days"] == 730  # clamped


def test_daily_history_carries_the_latest_counts_forward():
    day1 = datetime(2026, 1, 1, 9)
    day2 = datetime(2026, 1, 2, 9)
    counts = lambda total: {"violations": {"total": total, "critical": 0, "serious": 0, "moderate": 0, "minor": 0}}
    rows = [
        (1, day1, counts(5)),
        (2, day1, counts(3)),
        (1, day2, counts(1)),  # only page 1 rescanned on day 2; page 2 keeps its 3
    ]
    points = daily_history(rows)
    assert [p["date"] for p in points] == ["2026-01-01", "2026-01-02"]
    assert points[0]["report_counts"]["violations"]["total"] == 8
    assert points[1]["report_counts"]["violations"]["total"] == 4
    assert daily_history([]) == []

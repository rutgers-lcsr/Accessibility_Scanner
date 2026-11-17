"""Website inventory: lifecycle status and sunset date, department, business owner,
audience and criticality; who may set them, the list filters, and retired websites
dropping out of scheduled scans and owner digests."""
import types
from datetime import date, timedelta

import pytest

import models.website as website_models
import services.scan as scan_service
from models import db


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setattr(website_models, "is_valid_url", lambda url: True)


def _patch(client, jwt_header, user, website, body):
    return client.patch(f"/api/websites/{website.id}/", json=body, headers=jwt_header(user))


def test_new_website_is_live_with_empty_inventory(app, make_user, make_website):
    data = make_website(make_user()).to_dict()
    assert data["lifecycle_status"] == "live"
    assert data["sunset_date"] is None and data["past_sunset"] is False
    assert data["department"] is None and data["audience"] is None and data["criticality"] is None


def test_admin_sets_every_inventory_field(client, jwt_header, make_user, make_website):
    admin = make_user("root", is_admin=True)
    website = make_website(make_user())
    resp = _patch(client, jwt_header, admin, website, {
        "lifecycle_status": "retiring", "sunset_date": "2027-06-30", "department": " Computer Science ",
        "business_owner": "Dana Chair", "audience": "students", "criticality": "high"})
    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    assert body["lifecycle_status"] == "retiring"
    assert body["sunset_date"] == "2027-06-30"
    assert body["department"] == "Computer Science"
    assert body["business_owner"] == "Dana Chair"
    assert body["audience"] == "students" and body["criticality"] == "high"


def test_owner_sets_accountability_but_not_lifecycle_or_criticality(client, jwt_header, make_user, make_website):
    owner = make_user()
    website = make_website(owner)
    resp = _patch(client, jwt_header, owner, website, {
        "department": "CS", "audience": "public", "lifecycle_status": "retired", "criticality": "low",
        "sunset_date": "2020-01-01"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["department"] == "CS" and body["audience"] == "public"
    assert body["lifecycle_status"] == "live" and body["criticality"] is None and body["sunset_date"] is None


@pytest.mark.parametrize("body", [
    {"audience": "everyone"},
    {"lifecycle_status": "gone"},
    {"criticality": "extreme"},
    {"sunset_date": "next week"},
    {"department": 5},
    {"department": "x" * 201},
])
def test_invalid_inventory_values_are_rejected(client, jwt_header, make_user, make_website, body):
    admin = make_user("root", is_admin=True)
    website = make_website(make_user())
    resp = _patch(client, jwt_header, admin, website, body)
    assert resp.status_code == 400


def test_empty_values_clear_fields(client, jwt_header, make_user, make_website):
    admin = make_user("root", is_admin=True)
    website = make_website(make_user())
    _patch(client, jwt_header, admin, website, {"department": "CS", "audience": "public", "sunset_date": "2027-01-01"})
    body = _patch(client, jwt_header, admin, website, {"department": "", "audience": None, "sunset_date": ""}).get_json()
    assert body["department"] is None and body["audience"] is None and body["sunset_date"] is None


def test_past_sunset_flags_websites_not_yet_retired(app, make_user, make_website):
    website = make_website(make_user())
    website.sunset_date = date.today() - timedelta(days=1)
    website.lifecycle_status = "retiring"
    assert website.past_sunset() is True
    website.lifecycle_status = "retired"
    assert website.past_sunset() is False
    website.lifecycle_status = "live"
    website.sunset_date = date.today() + timedelta(days=1)
    assert website.past_sunset() is False


def test_list_filters_by_inventory_fields(client, jwt_header, make_user, make_website):
    admin = make_user("root", is_admin=True)
    owner = make_user()
    cs = make_website(owner, base="https://cs.example")
    cs.department, cs.lifecycle_status = "CS", "live"
    math = make_website(owner, base="https://math.example")
    math.department, math.lifecycle_status, math.criticality = "Math", "retired", "low"
    db.session.commit()

    def urls(query):
        resp = client.get(f"/api/websites/?{query}", headers=jwt_header(admin))
        return sorted(item["url"] for item in resp.get_json()["items"])

    assert urls("department=CS") == ["https://cs.example"]
    assert urls("lifecycle=live,retiring") == ["https://cs.example"]
    assert urls("criticality=low") == ["https://math.example"]
    assert urls("department=CS,Math") == ["https://cs.example", "https://math.example"]


def test_departments_lists_distinct_names_the_caller_can_see(client, jwt_header, make_user, make_website):
    alice, bob = make_user("alice"), make_user("bob")
    mine = make_website(alice, base="https://a.example")
    mine.department = "CS"
    other = make_website(bob, base="https://b.example")
    other.department = "Math"
    also_mine = make_website(alice, base="https://c.example")
    also_mine.department = "CS"
    db.session.commit()
    assert client.get("/api/websites/departments/", headers=jwt_header(alice)).get_json() == ["CS"]
    admin = make_user("root", is_admin=True)
    assert client.get("/api/websites/departments/", headers=jwt_header(admin)).get_json() == ["CS", "Math"]


def test_retired_websites_are_not_scheduled(app, make_user, make_website, monkeypatch):
    from scanner.tasks import check_and_queue_scans

    owner = make_user()
    live = make_website(owner, base="https://live.example")
    retired = make_website(owner, base="https://retired.example")
    for website in (live, retired):
        website.active = True
        website.last_scanned = None
    retired.lifecycle_status = "retired"
    db.session.commit()
    queued = []
    monkeypatch.setattr(scan_service.scan_website_task, "delay",
                        lambda url: queued.append(url) or types.SimpleNamespace(id=f"t-{len(queued)}"))

    assert check_and_queue_scans.run() == {"checked": 1, "queued": 1}
    assert queued == ["https://live.example"]


def test_retired_websites_leave_owner_digests(app, make_user, make_website):
    from services.owner_digest import owner_websites

    owner = make_user()
    live = make_website(owner, base="https://live.example")
    retired = make_website(owner, base="https://retired.example")
    retired.lifecycle_status = "retired"
    db.session.commit()
    assert [w.url for w in owner_websites(owner)] == [live.url]

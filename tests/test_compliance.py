"""Compliance: finding deadlines, the exceptions register, manual reviews and the agent
prompt and submission."""
from datetime import date, datetime, timedelta

import pytest

import models.website as website_models
from models import db
from models.compliance import ComplianceException, ManualReview
from models.finding import Finding
from services.compliance import compliance_counts, deadline_info, due_at, sla_days
from services.findings import fix_first, list_findings, sync_report_findings
from services.reviews import CHECKLIST_KEYS, agent_prompt, clean_results


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setattr(website_models, "is_valid_url", lambda url: True)


def _violation(rule="color-contrast", impact="serious", target="div.banner"):
    return {"id": rule, "impact": impact, "help": "h", "helpUrl": "u",
            "nodes": [{"target": [target], "html": f"<div class='{target}'>x</div>"}]}


def _page_with_finding(add_report, site, first_seen, rule="color-contrast", impact="serious"):
    report = add_report(site, violations=[_violation(rule, impact)])
    sync_report_findings(site.id, report.id, report.timestamp, report.report["violations"])
    db.session.query(Finding).filter_by(site_id=site.id, rule_id=rule).update({"first_seen": first_seen})
    db.session.commit()
    return report


# --- deadlines ------------------------------------------------------------------------------------


def test_sla_defaults_and_due_at(app):
    assert sla_days() == {"critical": 30, "serious": 60, "moderate": 90, "minor": 180}
    seen = datetime(2026, 1, 1)
    assert due_at(seen, "critical", sla_days()) == datetime(2026, 1, 31)
    assert due_at(seen, "minor", {"minor": 0}) is None
    assert due_at(None, "critical", sla_days()) is None


def test_deadline_info_overdue_unless_excepted(app):
    sla, now = sla_days(), datetime(2026, 6, 1)
    old = datetime(2026, 1, 1)
    assert deadline_info("r", "serious", old, "open", "https://e/x", [], sla, now)["overdue"] is True
    assert deadline_info("r", "serious", old, "fixed", "https://e/x", [], sla, now) == {
        "due_at": None, "overdue": False, "exception_id": None}
    exc = ComplianceException(id=7, rule_id="r", url_prefix="https://e/", status="approved", expires_on=None)
    info = deadline_info("r", "serious", old, "open", "https://e/x", [exc], sla, now)
    assert info["overdue"] is False and info["exception_id"] == 7
    assert deadline_info("other", "serious", old, "open", "https://e/x", [exc], sla, now)["overdue"] is True


def test_exception_scope_and_expiry():
    exc = ComplianceException(rule_id=None, url_prefix="https://e.com/archive/", status="approved",
                              expires_on=date(2026, 12, 31))
    assert exc.covers("any-rule", "https://e.com/archive/2010.html")
    assert not exc.covers("any-rule", "https://e.com/news/")
    assert exc.is_active(date(2026, 12, 31)) and not exc.is_active(date(2027, 1, 1))
    assert exc.display_status(date(2027, 1, 1)) == "expired"
    exc.status = "requested"
    assert not exc.is_active(date(2026, 1, 1))


def test_listing_and_fix_first_report_deadlines(app, make_user, make_website, add_site, add_report):
    website = make_website(make_user())
    archive, news = add_site(website, "/archive/old"), add_site(website, "/news")
    long_ago = datetime.utcnow() - timedelta(days=400)
    _page_with_finding(add_report, archive, long_ago)
    _page_with_finding(add_report, news, long_ago)
    db.session.add(ComplianceException(website_id=website.id, url_prefix=website.url + "/archive/", kind="archived",
                                       reason="Archived", status="approved", requested_at=datetime.utcnow()))
    db.session.commit()

    listing = list_findings([archive.id, news.id])
    rule = listing["rules"][0]
    by_url = {page["url"]: page["findings"][0] for page in rule["pages"]}
    assert by_url[news.url]["overdue"] is True and by_url[news.url]["due_at"]
    assert by_url[archive.url]["overdue"] is False and by_url[archive.url]["exception_id"] is not None
    assert rule["overdue"] == 1

    ranked = fix_first([archive.id, news.id])["rules"][0]
    assert ranked["overdue"] == 1 and ranked["next_due"] is not None

    counts = compliance_counts([website.id])[website.id]
    assert counts["overdue"] == 1 and counts["excepted"] == 1 and counts["active_exceptions"] == 1


def test_due_soon_counts(app, make_user, make_website, add_site, add_report):
    website = make_website(make_user())
    page = add_site(website, "/p")
    _page_with_finding(add_report, page, datetime.utcnow() - timedelta(days=55))  # serious: due in ~5 days
    counts = compliance_counts([website.id])[website.id]
    assert counts["due_soon"] == 1 and counts["overdue"] == 0
    assert website.to_dict()["compliance"]["review_due"] is True


# --- exceptions API --------------------------------------------------------------------------------


def test_exception_request_approve_flow(client, jwt_header, make_user, make_website):
    admin, owner, stranger = make_user("root", is_admin=True), make_user("owner"), make_user("stranger")
    website = make_website(owner)
    url = f"/api/websites/{website.id}/exceptions/"
    body = {"kind": "archived", "reason": "Old course pages kept for the record", "url_prefix": website.url + "/archive/"}

    assert client.post(url, json=body, headers=jwt_header(stranger)).status_code == 403
    assert client.post(url, json={**body, "reason": "  "}, headers=jwt_header(owner)).status_code == 400
    assert client.post(url, json={**body, "kind": "because"}, headers=jwt_header(owner)).status_code == 400
    assert client.post(url, json={**body, "url_prefix": "https://elsewhere.org/"}, headers=jwt_header(owner)).status_code == 400

    # An owner's request stays requested even if they send status.
    resp = client.post(url, json={**body, "status": "approved"}, headers=jwt_header(owner))
    assert resp.status_code == 201 and resp.get_json()["status"] == "requested"
    exc_id = resp.get_json()["id"]

    # Owners may not decide.
    resp = client.patch(f"/api/exceptions/{exc_id}/", json={"status": "approved"}, headers=jwt_header(owner))
    assert resp.status_code == 200 and resp.get_json()["status"] == "requested"

    resp = client.patch(f"/api/exceptions/{exc_id}/", json={"status": "approved", "expires_on": "2099-01-01",
                                                            "decision_note": "OK for a year"}, headers=jwt_header(admin))
    data = resp.get_json()
    assert data["status"] == "approved" and data["decided_by"] == "root" and data["expires_on"] == "2099-01-01"

    # Once decided the owner can no longer change or withdraw it.
    assert client.patch(f"/api/exceptions/{exc_id}/", json={"reason": "x"}, headers=jwt_header(owner)).status_code == 403
    assert client.delete(f"/api/exceptions/{exc_id}/", headers=jwt_header(owner)).status_code == 403

    listed = client.get(url, headers=jwt_header(owner)).get_json()
    assert [e["id"] for e in listed] == [exc_id]
    assert client.get("/api/exceptions/", headers=jwt_header(owner)).status_code == 403
    register = client.get("/api/exceptions/?status=approved", headers=jwt_header(admin)).get_json()
    assert [e["website_url"] for e in register] == [website.url]


def test_admin_records_approved_exception_directly(client, jwt_header, make_user, make_website):
    admin = make_user("root", is_admin=True)
    website = make_website(make_user())
    resp = client.post(f"/api/websites/{website.id}/exceptions/", headers=jwt_header(admin), json={
        "kind": "third_party", "reason": "Vendor widget", "rule_id": "frame-title", "status": "approved",
        "expires_on": "2020-01-01"})
    assert resp.status_code == 201 and resp.get_json()["status"] == "expired"


def test_owner_withdraws_request(client, jwt_header, make_user, make_website):
    owner = make_user("owner")
    website = make_website(owner)
    resp = client.post(f"/api/websites/{website.id}/exceptions/", json={"kind": "other", "reason": "x"},
                       headers=jwt_header(owner))
    assert client.delete(f"/api/exceptions/{resp.get_json()['id']}/", headers=jwt_header(owner)).status_code == 204
    assert db.session.query(ComplianceException).count() == 0


# --- reviews ---------------------------------------------------------------------------------------


def test_clean_results_validates():
    assert clean_results({"keyboard": "pass"}) == {"keyboard": {"result": "pass", "notes": None, "pages": []}}
    with pytest.raises(ValueError):
        clean_results({"nope": "pass"})
    with pytest.raises(ValueError):
        clean_results({"keyboard": {"result": "great"}})
    with pytest.raises(ValueError):
        clean_results({"keyboard": {"result": "fail", "pages": "https://x"}})


def test_review_lifecycle(client, jwt_header, make_user, make_website):
    owner, stranger = make_user("owner"), make_user("stranger")
    website = make_website(owner)
    url = f"/api/websites/{website.id}/reviews/"
    assert client.post(url, json={}, headers=jwt_header(stranger)).status_code == 403
    resp = client.post(url, json={"pages": [website.url + "/"], "results": {"keyboard": "pass"}}, headers=jwt_header(owner))
    assert resp.status_code == 201
    review = resp.get_json()
    assert review["status"] == "in_progress" and review["reviewer"] == "owner" and review["source"] == "person"

    resp = client.patch(f"{url}{review['id']}/", headers=jwt_header(owner), json={
        "results": {"zoom": {"result": "fail", "notes": "Menu overlaps at 200%", "pages": [website.url + "/"]}},
        "status": "completed", "summary": "Zoom breaks the menu."})
    data = resp.get_json()
    assert set(data["results"]) == {"keyboard", "zoom"}  # merged
    assert data["counts"]["pass"] == 1 and data["counts"]["fail"] == 1
    assert data["status"] == "completed" and data["completed_at"]
    assert website.to_dict()["compliance"]["review_due"] is False

    assert client.get(url, headers=jwt_header(owner)).get_json()[0]["id"] == review["id"]
    assert client.patch(f"{url}{review['id']}/", json={"status": "done"}, headers=jwt_header(owner)).status_code == 400
    assert client.delete(f"{url}{review['id']}/", headers=jwt_header(owner)).status_code == 204


def test_checklist_and_prompt(client, jwt_header, make_user, make_website, add_site):
    owner = make_user("owner")
    website = make_website(owner)
    add_site(website, "/")
    add_site(website, "/about")
    add_site(website, "/a/b/c")
    checklist = client.get("/api/reviews/checklist/", headers=jwt_header(owner)).get_json()
    assert [item["key"] for item in checklist] == list(CHECKLIST_KEYS)

    body = client.get(f"/api/websites/{website.id}/reviews/prompt/", headers=jwt_header(owner)).get_json()
    assert body["pages"][0] == website.url + "/"
    assert body["pages"][-1] == website.url + "/a/b/c"
    prompt = body["prompt"]
    assert f"/api/v1/websites/{website.id}/reviews" in prompt
    assert all(f"`{key}`" in prompt for key in CHECKLIST_KEYS)
    assert "Do not submit forms" in prompt


def test_agent_submits_review_with_api_key(client, make_user, make_website, make_api_key):
    owner, stranger = make_user("owner"), make_user("stranger")
    website = make_website(owner)
    _, token = make_api_key(owner)
    _, other_token = make_api_key(stranger)
    url = f"/api/v1/websites/{website.id}/reviews"
    body = {"tool": "Claude agent", "pages": [website.url], "summary": "Mostly fine.",
            "results": {key: {"result": "pass"} for key in CHECKLIST_KEYS}}

    assert client.post(url, json=body).status_code == 401
    assert client.post(url, json=body, headers={"X-API-Key": other_token}).status_code == 403
    assert client.post(url, json={**body, "results": {"keyboard": "maybe"}}, headers={"X-API-Key": token}).status_code == 400
    resp = client.post(url, json=body, headers={"X-API-Key": token})
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["source"] == "agent" and data["tool"] == "Claude agent" and data["status"] == "completed"
    assert data["counts"]["pass"] == len(CHECKLIST_KEYS)


def test_deleting_a_website_removes_compliance_records(app, make_user, make_website):
    website = make_website(make_user())
    db.session.add(ComplianceException(website_id=website.id, kind="other", reason="x", requested_at=datetime.utcnow()))
    db.session.add(ManualReview(website_id=website.id, started_at=datetime.utcnow()))
    db.session.commit()
    website.delete()
    assert db.session.query(ComplianceException).count() == 0 and db.session.query(ManualReview).count() == 0


def test_prompt_text_is_self_contained(app, make_user, make_website):
    website = make_website(make_user())
    prompt = agent_prompt(website, "https://a11y.example.edu", [website.url])
    assert "https://a11y.example.edu/api/v1/websites" in prompt and website.url in prompt

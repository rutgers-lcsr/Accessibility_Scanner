"""Verify my fix: a single-page scan runs on its own queue, is flagged from the moment
it is queued, and reports the id of the report it produced."""
import pytest

import scanner.tasks as tasks_mod
import services.scan as scan_service


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    import models.website as website_models
    monkeypatch.setattr(website_models, "is_valid_url", lambda url: True)


class _Task:
    def __init__(self, task_id):
        self.id = task_id


def test_page_scans_are_routed_to_their_own_queue():
    from celery_app import celery

    route = lambda name: celery.amqp.router.route({}, name)["queue"].name
    assert route("scanner.tasks.scan_site") == "pages"
    assert route("scanner.tasks.quick_scan") == "pages"
    assert route("scanner.tasks.scan_website") == "celery"
    assert tasks_mod.scan_site.soft_time_limit == 300 and tasks_mod.scan_site.time_limit == 360


def test_the_task_result_names_the_report(monkeypatch):
    async def fake_scan(url):
        return 42

    monkeypatch.setattr(tasks_mod, "async_generate_single_site_report", fake_scan)
    monkeypatch.setattr(tasks_mod.scan_site, "update_state", lambda *a, **k: None)

    result = tasks_mod.scan_site.run("https://example.com/page")

    assert result["status"] == "completed" and result["report_id"] == 42


def test_queueing_flags_the_page_until_the_scanner_clears_it(client, make_user, make_site, jwt_header, monkeypatch):
    from datetime import timedelta
    from models import db

    user = make_user()
    site = make_site(user)
    calls = []
    monkeypatch.setattr(scan_service.scan_site_task, "delay", lambda url: calls.append(url) or _Task("site-task-1"))

    assert client.post(f"/api/scans/scan/?site={site.id}", headers=jwt_header(user)).status_code == 202
    assert site.scanning is True and scan_service.site_scan_in_progress(site)
    # a second click while the task is still queued
    assert client.post(f"/api/scans/scan/?site={site.id}", headers=jwt_header(user)).status_code == 409
    assert calls == [site.url]

    # a lost task: the flag expires after the page window, not the crawl window
    site.scan_queued_at = scan_service._utcnow() - scan_service.SITE_STALE_AFTER - timedelta(minutes=1)
    db.session.commit()
    assert not scan_service.site_scan_in_progress(site)
    assert client.post(f"/api/scans/scan/?site={site.id}", headers=jwt_header(user)).status_code == 202


def test_status_exposes_the_report_id_on_both_surfaces(client, make_user, make_site, make_api_key, jwt_header, monkeypatch):
    from models import db
    from tests.test_scan_api import _FakeAsyncResult

    user = make_user()
    site = make_site(user)
    site.last_task_id = "site-task-9"
    db.session.commit()
    fake = _FakeAsyncResult(state="SUCCESS", result={"status": "completed", "report_id": 5})
    monkeypatch.setattr("celery.result.AsyncResult", lambda task_id, app=None: fake)

    jwt = client.get("/api/scans/status/site-task-9", headers=jwt_header(user)).get_json()
    assert jwt["state"] == "SUCCESS" and jwt["result"]["report_id"] == 5

    _, token = make_api_key(user)
    api = client.get("/api/v1/scans/site-task-9", headers={"X-API-Key": token}).get_json()
    assert api["result"]["report_id"] == 5


def test_report_payload_says_who_may_rescan(client, make_user, make_website, add_site, add_report, jwt_header):
    from models import db

    owner = make_user("alice")
    member = make_user("bob")
    stranger = make_user("carol")
    admin = make_user("root", is_admin=True)
    website = make_website(owner, public=True)
    website.users.append(member)
    db.session.commit()
    report = add_report(add_site(website))

    can_scan = lambda headers=None: client.get(f"/api/reports/{report.id}/", headers=headers).get_json()["can_scan"]
    assert can_scan(jwt_header(owner)) and can_scan(jwt_header(member)) and can_scan(jwt_header(admin))
    assert not can_scan(jwt_header(stranger)) and not can_scan()


def test_website_report_pages_carry_their_site_id(client, make_user, make_website, add_site, add_report, jwt_header):
    owner = make_user()
    website = make_website(owner)
    home = add_site(website, page="/")
    add_report(home)

    payload = client.get(f"/api/websites/{website.id}/", headers=jwt_header(owner)).get_json()
    pages = payload["report"]["violations"][0]["reports"]
    assert pages[0]["site_id"] == home.id and pages[0]["url"] == home.url

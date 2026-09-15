"""JWT scan endpoints: task recording, status ownership, ACE config access, rate limiting."""
import types

import services.scan as scan_service


class _FakeAsyncResult:
    def __init__(self, state="PENDING", info=None, result=None):
        self.state = state
        self.info = info
        self.result = result


def _fake_delay(task_id):
    return lambda url: types.SimpleNamespace(id=task_id)


# --- triggering ---------------------------------------------------------------


def test_jwt_website_scan_records_task_ids(client, make_user, make_site, jwt_header, monkeypatch):
    user = make_user()
    website = make_site(user).websites.first()
    monkeypatch.setattr(scan_service.scan_website_task, "delay", _fake_delay("jwt-task-1"))

    resp = client.post(f"/api/scans/scan/?website={website.id}", headers=jwt_header(user))
    assert resp.status_code == 202
    body = resp.get_json()
    assert body["task_id"] == "jwt-task-1"
    assert body["status_endpoint"] == "/api/scans/status/jwt-task-1"
    assert website.current_task_id == "jwt-task-1"
    assert website.last_task_id == "jwt-task-1"


def test_jwt_website_scan_reports_existing_task(client, make_user, make_site, jwt_header, monkeypatch):
    from models import db

    user = make_user()
    website = make_site(user).websites.first()
    website.current_task_id = "running"
    db.session.commit()
    monkeypatch.setattr(
        scan_service.scan_website_task, "AsyncResult", lambda task_id: _FakeAsyncResult("PROGRESS")
    )
    monkeypatch.setattr(
        scan_service.scan_website_task,
        "delay",
        lambda url: (_ for _ in ()).throw(AssertionError("should not queue")),
    )

    resp = client.post(f"/api/scans/scan/?website={website.id}", headers=jwt_header(user))
    assert resp.status_code == 202
    body = resp.get_json()
    assert body["task_id"] == "running"
    assert body["info"] == "Scan already in progress"


def test_jwt_site_scan_records_task_id(client, make_user, make_site, jwt_header, monkeypatch):
    user = make_user()
    site = make_site(user)
    monkeypatch.setattr(scan_service.scan_site_task, "delay", _fake_delay("site-task-1"))

    resp = client.post(f"/api/scans/scan/?site={site.id}", headers=jwt_header(user))
    assert resp.status_code == 202
    assert resp.get_json()["task_id"] == "site-task-1"
    # the JWT path used to queue site scans without remembering the task at all
    assert site.last_task_id == "site-task-1"


# --- status ownership -----------------------------------------------------------


def test_task_status_visible_to_owner_only(client, make_user, make_site, jwt_header, monkeypatch):
    from models import db

    owner = make_user("bob")
    other = make_user("alice")
    website = make_site(owner).websites.first()
    website.last_task_id = "t-42"
    db.session.commit()

    fake = _FakeAsyncResult("SUCCESS", result={"reports_generated": 1})
    monkeypatch.setattr("celery.result.AsyncResult", lambda task_id, app=None: fake)

    assert client.get("/api/scans/status/t-42", headers=jwt_header(other)).status_code == 404
    assert client.get("/api/scans/status/unknown", headers=jwt_header(owner)).status_code == 404

    resp = client.get("/api/scans/status/t-42", headers=jwt_header(owner))
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["state"] == "SUCCESS" and body["result"] == {"reports_generated": 1}


def test_task_status_resolves_site_tasks(client, make_user, make_site, jwt_header, monkeypatch):
    from models import db

    user = make_user()
    site = make_site(user)
    site.last_task_id = "s-7"
    db.session.commit()

    fake = _FakeAsyncResult("PROGRESS", info={"status": "Scanning", "current": 1, "total": 1})
    monkeypatch.setattr("celery.result.AsyncResult", lambda task_id, app=None: fake)

    resp = client.get("/api/scans/status/s-7", headers=jwt_header(user))
    assert resp.status_code == 200
    assert resp.get_json()["current"] == 1


# --- ACE config -----------------------------------------------------------------


def test_ace_config_requires_view_permission(client, make_user, make_site, jwt_header):
    owner = make_user("bob")
    other = make_user("alice")
    website = make_site(owner).websites.first()
    url = f"/api/websites/{website.id}/axe/"

    assert client.get(url).status_code == 403  # anonymous, private website
    assert client.get(url, headers=jwt_header(other)).status_code == 403
    assert client.get(url, headers=jwt_header(owner)).status_code == 200


def test_ace_config_of_public_website_is_readable_anonymously(client, make_user, make_site):
    website = make_site(make_user(), public=True).websites.first()
    assert client.get(f"/api/websites/{website.id}/axe/").status_code == 200


# --- rate limiting --------------------------------------------------------------


def test_scan_trigger_is_rate_limited(make_user, make_site, jwt_header, monkeypatch):
    from app import create_app

    user = make_user()
    website = make_site(user).websites.first()
    headers = jwt_header(user)
    monkeypatch.setattr(scan_service.scan_website_task, "delay", _fake_delay("t"))
    monkeypatch.setattr(
        scan_service.scan_website_task, "AsyncResult", lambda task_id: _FakeAsyncResult("SUCCESS")
    )

    # The shared test app runs with the limiter off; build one with it on.
    monkeypatch.setenv("RATELIMIT_ENABLED", "True")
    limited = create_app().test_client()

    codes = [
        limited.post(f"/api/scans/scan/?website={website.id}", headers=headers).status_code
        for _ in range(6)
    ]
    assert codes[:5] == [202] * 5
    assert codes[5] == 429

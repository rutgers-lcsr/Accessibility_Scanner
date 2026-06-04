"""Tests for the scan trigger + status endpoints (celery mocked)."""
import types

import blueprints.api as api


def _key_header(token):
    return {"X-API-Key": token}


class _FakeAsyncResult:
    """Stand-in for celery AsyncResult, configured per test."""

    def __init__(self, state="PENDING", info=None, result=None):
        self.state = state
        self.info = info
        self.result = result


# --- website scan -----------------------------------------------------------


def test_scan_website_queues_task(
    client, make_user, make_site, make_api_key, monkeypatch
):
    user = make_user()
    site = make_site(user)
    website = site.websites.first()
    _, token = make_api_key(user)

    monkeypatch.setattr(
        api.scan_website_task, "delay", lambda url: types.SimpleNamespace(id="task-123")
    )

    resp = client.post(
        f"/api/v1/websites/{website.id}/scan", headers=_key_header(token)
    )
    assert resp.status_code == 202
    body = resp.get_json()
    assert body["task_id"] == "task-123"
    assert body["status_endpoint"] == "/api/v1/scans/task-123"
    # the website now tracks the running task
    assert website.current_task_id == "task-123"


def test_scan_website_missing(client, make_user, make_api_key):
    user = make_user()
    _, token = make_api_key(user)
    resp = client.post("/api/v1/websites/999999/scan", headers=_key_header(token))
    assert resp.status_code == 404


def test_scan_website_forbidden_for_non_owner(
    client, make_user, make_site, make_api_key
):
    owner = make_user("bob")
    other = make_user("alice")
    website = make_site(owner).websites.first()
    _, token = make_api_key(other)
    resp = client.post(
        f"/api/v1/websites/{website.id}/scan", headers=_key_header(token)
    )
    assert resp.status_code == 403


def test_scan_website_already_in_progress(
    client, make_user, make_site, make_api_key, monkeypatch
):
    from models import db

    user = make_user()
    website = make_site(user).websites.first()
    website.current_task_id = "running-task"
    db.session.commit()
    _, token = make_api_key(user)

    monkeypatch.setattr(
        api.scan_website_task,
        "AsyncResult",
        lambda task_id: _FakeAsyncResult(state="PROGRESS"),
    )
    # delay must NOT be called when a scan is already running
    monkeypatch.setattr(
        api.scan_website_task,
        "delay",
        lambda url: (_ for _ in ()).throw(AssertionError("should not queue")),
    )

    resp = client.post(
        f"/api/v1/websites/{website.id}/scan", headers=_key_header(token)
    )
    assert resp.status_code == 202
    assert resp.get_json()["task_id"] == "running-task"


# --- site scan --------------------------------------------------------------


def test_scan_site_queues_task(
    client, make_user, make_site, make_api_key, monkeypatch
):
    user = make_user()
    site = make_site(user)
    _, token = make_api_key(user)

    monkeypatch.setattr(
        api.scan_site_task, "delay", lambda url: types.SimpleNamespace(id="site-task-9")
    )

    resp = client.post(f"/api/v1/sites/{site.id}/scan", headers=_key_header(token))
    assert resp.status_code == 202
    assert resp.get_json()["task_id"] == "site-task-9"


def test_scan_site_already_scanning(
    client, make_user, make_site, make_api_key
):
    from models import db

    user = make_user()
    site = make_site(user)
    site.scanning = True
    db.session.commit()
    _, token = make_api_key(user)

    resp = client.post(f"/api/v1/sites/{site.id}/scan", headers=_key_header(token))
    assert resp.status_code == 409


# --- scan status ------------------------------------------------------------


def test_scan_status_success(client, make_user, make_api_key, monkeypatch):
    user = make_user()
    _, token = make_api_key(user)

    fake = _FakeAsyncResult(state="SUCCESS", result={"reports_generated": 3})
    monkeypatch.setattr("celery.result.AsyncResult", lambda task_id, app=None: fake)

    resp = client.get("/api/v1/scans/task-123", headers=_key_header(token))
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["state"] == "SUCCESS"
    assert body["result"] == {"reports_generated": 3}


def test_scan_status_progress(client, make_user, make_api_key, monkeypatch):
    user = make_user()
    _, token = make_api_key(user)

    fake = _FakeAsyncResult(
        state="PROGRESS", info={"status": "Scanning", "current": 2, "total": 5}
    )
    monkeypatch.setattr("celery.result.AsyncResult", lambda task_id, app=None: fake)

    resp = client.get("/api/v1/scans/task-123", headers=_key_header(token))
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["state"] == "PROGRESS"
    assert body["current"] == 2 and body["total"] == 5


def test_scan_status_requires_key(client):
    assert client.get("/api/v1/scans/whatever").status_code == 401

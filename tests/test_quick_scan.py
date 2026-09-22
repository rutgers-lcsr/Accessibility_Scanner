"""Quick scans: the request checks (public host, allowed domain, reachable, one at a
time), ownership of status and result, the result shape and bounds, and the task."""
import base64
import io
import types
from datetime import timedelta

import pytest

import blueprints.scan as scan_bp
import models.website as website_models
import services.quick_scan as quick_service
from services.quick_scan import QUICK_SCAN_MAX_NODES, QUICK_SCAN_MAX_PHOTO_BYTES, shape_result


class _FakeAsyncResult:
    def __init__(self, state="PENDING", info=None, result=None):
        self.state = state
        self.info = info
        self.result = result


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setattr(website_models, "is_valid_url", lambda url: True)
    monkeypatch.setattr(scan_bp, "is_safe_target", lambda url: True)
    monkeypatch.setattr(scan_bp, "check_url", lambda url: True)
    monkeypatch.setattr(quick_service.quick_scan_task, "delay", lambda url: types.SimpleNamespace(id="quick-1"))
    monkeypatch.setattr(quick_service.quick_scan_task, "AsyncResult", lambda task_id: _FakeAsyncResult("PENDING"))


def _allow(name="rutgers.edu"):
    from models import db
    from models.website import Domain

    domain = Domain(domain=name)
    db.session.add(domain)
    db.session.commit()


def _fake_state(monkeypatch, state, **kwargs):
    fake = _FakeAsyncResult(state, **kwargs)
    monkeypatch.setattr("celery.result.AsyncResult", lambda task_id, app=None: fake)
    monkeypatch.setattr(quick_service.quick_scan_task, "AsyncResult", lambda task_id: fake)
    return fake


# --- the request ---------------------------------------------------------------------------


def test_quick_scan_validates_the_url(client, make_user, jwt_header, monkeypatch):
    user = make_user()
    _allow()
    post = lambda url: client.post("/api/scans/quick/", json={"url": url}, headers=jwt_header(user))

    assert post("").status_code == 400
    assert post("cs.rutgers.edu/x").status_code == 400
    assert post("ftp://cs.rutgers.edu/x").status_code == 400
    monkeypatch.setattr(scan_bp, "is_safe_target", lambda url: False)
    assert "not public" in post("https://cs.rutgers.edu/x").get_json()["error"]
    monkeypatch.setattr(scan_bp, "is_safe_target", lambda url: True)
    monkeypatch.setattr(scan_bp, "check_url", lambda url: False)
    assert "not reachable" in post("https://cs.rutgers.edu/x").get_json()["error"]
    assert client.post("/api/scans/quick/", json={"url": "https://cs.rutgers.edu/"}).status_code == 401


def test_quick_scan_is_limited_to_allowed_domains(client, make_user, jwt_header):
    from models import db
    from models.quick_scan import QuickScan

    user = make_user()
    _allow("rutgers.edu")

    resp = client.post("/api/scans/quick/", json={"url": "https://example.org/page"}, headers=jwt_header(user))
    assert resp.status_code == 400
    body = resp.get_json()
    assert body["code"] == "not_allowed_domain" and body["domain"] == "example.org"
    assert db.session.query(QuickScan).count() == 0

    resp = client.post("/api/scans/quick/", json={"url": "https://cs.rutgers.edu/people#staff"}, headers=jwt_header(user))
    assert resp.status_code == 202
    body = resp.get_json()
    assert body["task_id"] == "quick-1" and body["url"] == "https://cs.rutgers.edu/people"
    assert body["status_endpoint"] == "/api/scans/status/quick-1"
    assert body["result_endpoint"] == "/api/scans/quick/quick-1/"
    row = db.session.query(QuickScan).one()
    assert row.user_id == user.id and row.url == "https://cs.rutgers.edu/people"


def test_one_quick_scan_at_a_time_per_user(client, make_user, jwt_header, monkeypatch):
    user = make_user()
    _allow()
    headers = jwt_header(user)
    assert client.post("/api/scans/quick/", json={"url": "https://cs.rutgers.edu/"}, headers=headers).status_code == 202

    _fake_state(monkeypatch, "PROGRESS", info={"status": "Loading the page…"})
    assert client.post("/api/scans/quick/", json={"url": "https://cs.rutgers.edu/"}, headers=headers).status_code == 409

    _fake_state(monkeypatch, "SUCCESS", result={"status": "completed"})
    monkeypatch.setattr(quick_service.quick_scan_task, "delay", lambda url: types.SimpleNamespace(id="quick-2"))
    assert client.post("/api/scans/quick/", json={"url": "https://cs.rutgers.edu/"}, headers=headers).status_code == 202


# --- status and result ownership -------------------------------------------------------------


def test_status_and_result_are_visible_to_the_owner_and_admins_only(client, make_user, jwt_header, monkeypatch):
    owner = make_user("alice")
    other = make_user("bob")
    admin = make_user("root", is_admin=True)
    _allow()
    client.post("/api/scans/quick/", json={"url": "https://cs.rutgers.edu/"}, headers=jwt_header(owner))
    _fake_state(monkeypatch, "SUCCESS", result={"status": "completed", "url": "https://cs.rutgers.edu/", "report": {"violations": []},
                                                "photo": base64.b64encode(b"\x89PNG").decode(), "report_counts": {"violations": {"total": 0}}})

    assert client.get("/api/scans/status/quick-1", headers=jwt_header(other)).status_code == 404
    assert client.get("/api/scans/quick/quick-1/", headers=jwt_header(other)).status_code == 404
    assert client.get("/api/scans/quick/quick-1/photo/", headers=jwt_header(other)).status_code == 404

    status = client.get("/api/scans/status/quick-1", headers=jwt_header(owner)).get_json()
    assert status["state"] == "SUCCESS" and "report" not in status["result"] and "photo" not in status["result"]

    result = client.get("/api/scans/quick/quick-1/", headers=jwt_header(admin)).get_json()
    assert result["status"] == "completed" and result["photo_url"] == "/api/scans/quick/quick-1/photo/"
    assert "photo" not in result and result["report"] == {"violations": []}

    photo = client.get("/api/scans/quick/quick-1/photo/", headers=jwt_header(owner))
    assert photo.status_code == 200 and photo.data == b"\x89PNG" and photo.mimetype == "image/png"


def test_result_endpoint_reports_running_failed_and_expired(client, make_user, jwt_header, monkeypatch):
    from models import db
    from models.quick_scan import QuickScan

    user = make_user()
    _allow()
    headers = jwt_header(user)
    client.post("/api/scans/quick/", json={"url": "https://cs.rutgers.edu/"}, headers=headers)

    _fake_state(monkeypatch, "PROGRESS", info={"status": "Loading the page…"})
    resp = client.get("/api/scans/quick/quick-1/", headers=headers)
    assert resp.status_code == 202 and resp.get_json()["status"] == "Loading the page…"

    _fake_state(monkeypatch, "FAILURE", info=RuntimeError("time limit"))
    resp = client.get("/api/scans/quick/quick-1/", headers=headers)
    assert resp.status_code == 200 and resp.get_json()["state"] == "FAILURE" and "time limit" in resp.get_json()["error"]

    _fake_state(monkeypatch, "PENDING")
    row = db.session.query(QuickScan).one()
    row.created_at = row.created_at - timedelta(days=2)
    db.session.commit()
    assert client.get("/api/scans/quick/quick-1/", headers=headers).status_code == 410
    assert client.get("/api/scans/quick/quick-1/photo/", headers=headers).status_code == 404


def test_old_requests_are_pruned_when_a_new_one_is_queued(client, make_user, jwt_header, monkeypatch):
    from models import db
    from models.quick_scan import QuickScan

    user = make_user()
    _allow()
    headers = jwt_header(user)
    client.post("/api/scans/quick/", json={"url": "https://cs.rutgers.edu/"}, headers=headers)
    old = db.session.query(QuickScan).one()
    old.created_at = old.created_at - timedelta(days=2)
    db.session.commit()
    _fake_state(monkeypatch, "SUCCESS", result={})
    monkeypatch.setattr(quick_service.quick_scan_task, "delay", lambda url: types.SimpleNamespace(id="quick-2"))

    assert client.post("/api/scans/quick/", json={"url": "https://cs.rutgers.edu/"}, headers=headers).status_code == 202
    assert [row.task_id for row in db.session.query(QuickScan).all()] == ["quick-2"]


# --- result shape -------------------------------------------------------------------------------


def _png(width, height):
    from PIL import Image

    buffer = io.BytesIO()
    Image.effect_noise((width, height), 64).convert("RGB").save(buffer, format="PNG")
    return buffer.getvalue()


def test_shape_result_counts_caps_nodes_and_bounds_the_screenshot():
    nodes = [{"target": [f"#{i}"], "html": "<p>"} for i in range(QUICK_SCAN_MAX_NODES + 5)]
    report = {
        "url": "https://cs.rutgers.edu/", "timestamp": "2026-09-22T00:00:00Z", "response_code": 200, "tags": ["wcag2a"],
        "report": {"violations": [{"id": "color-contrast", "impact": "serious", "nodes": nodes}],
                   "incomplete": [{"id": "x", "impact": "minor", "nodes": nodes[:2]}],
                   "passes": [{"id": "p", "nodes": nodes}], "inapplicable": []},
        "photo": _png(20, 20), "links": ["a", "b"], "videos": [], "tabable": True,
    }

    result = shape_result(report)

    assert result["status"] == "completed" and result["error"] is None
    assert result["report_counts"]["violations"] == {"total": 1, "critical": 0, "serious": 1, "moderate": 0, "minor": 0}
    assert result["report_counts"]["passes"]["total"] == 1
    violation = result["report"]["violations"][0]
    assert len(violation["nodes"]) == QUICK_SCAN_MAX_NODES and violation["nodes_truncated"] == 5
    assert result["report"]["incomplete"][0]["nodes_truncated"] == 0
    assert "passes" not in result["report"]
    assert base64.b64decode(result["photo"]) == report["photo"] and result["photo_omitted"] is False
    assert result["links"] == 2 and result["tabable"] is True

    failed = shape_result({"url": "https://cs.rutgers.edu/x", "error": "Failed to load page, status code: 404", "response_code": 404})
    assert failed["status"] == "failed" and failed["report"] is None and failed["photo"] is None


def test_shape_result_downscales_or_drops_a_huge_screenshot(monkeypatch):
    big = _png(3000, 2600)
    assert len(big) > QUICK_SCAN_MAX_PHOTO_BYTES
    result = shape_result({"url": "u", "report": {"violations": []}, "photo": big})
    assert (result["photo"] is None and result["photo_omitted"]) or len(base64.b64decode(result["photo"])) <= QUICK_SCAN_MAX_PHOTO_BYTES

    monkeypatch.setattr(quick_service, "QUICK_SCAN_MAX_PHOTO_BYTES", 10)
    result = shape_result({"url": "u", "report": {"violations": []}, "photo": _png(50, 50)})
    assert result["photo"] is None and result["photo_omitted"] is True


# --- the task ---------------------------------------------------------------------------------


def test_quick_scan_task_runs_the_page_audit_and_shapes_it(app, monkeypatch):
    import scanner.tasks as tasks_mod

    seen = {}

    async def fake_run(url, tags, ace_config):
        seen.update(url=url, tags=tags, ace_config=ace_config)
        return {"url": url, "timestamp": "2026-09-22T00:00:00Z", "response_code": 200, "tags": tags,
                "report": {"violations": [{"id": "image-alt", "impact": "critical", "nodes": [{"target": ["img"]}]}]},
                "links": [], "videos": [], "tabable": False, "photo": None}

    monkeypatch.setattr(tasks_mod, "async_run_quick_scan", fake_run)
    monkeypatch.setattr(tasks_mod.quick_scan, "update_state", lambda *a, **k: None)

    result = tasks_mod.quick_scan.run("https://cs.rutgers.edu/")

    assert seen["url"] == "https://cs.rutgers.edu/" and "wcag2a" in seen["tags"]
    assert result["status"] == "completed" and result["report_counts"]["violations"]["critical"] == 1

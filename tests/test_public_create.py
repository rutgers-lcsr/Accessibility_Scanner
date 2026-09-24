"""Tests for adding websites through the API-key surface (POST /api/v1/websites)."""
import types

import pytest

import blueprints.website as website_bp
import models.website as website_models


@pytest.fixture(autouse=True)
def _no_dns(monkeypatch):
    # Domain/Website validation resolves hostnames; keep these tests offline.
    monkeypatch.setattr(website_models, "is_valid_url", lambda url: True)
    monkeypatch.setattr(website_bp, "is_valid_url", lambda url: True)


@pytest.fixture()
def created(monkeypatch):
    """Make the create path succeed offline: the probe passes and no scan is queued."""
    import scanner.tasks as tasks_mod

    monkeypatch.setattr(website_bp, "check_url", lambda url: True)
    monkeypatch.setattr(tasks_mod.scan_website, "delay", lambda url: types.SimpleNamespace(id="t-1"))


def _key_header(token):
    return {"X-API-Key": token}


def _domain(name, active=True):
    from models import db
    from models.website import Domain

    domain = Domain(domain=name)
    domain.active = active
    db.session.add(domain)
    db.session.commit()
    return domain


def _never(url):
    raise AssertionError("check_url must not run for a host outside the allow-list")


def _post(client, token, body):
    return client.post("/api/v1/websites", json=body, headers=_key_header(token))


def test_create_requires_key(client):
    resp = client.post("/api/v1/websites", json={"base_url": "https://cs.rutgers.edu/"})
    assert resp.status_code == 401


def test_create_website(client, make_user, make_api_key, created):
    from models import db
    from models.website import Website

    _domain("rutgers.edu")
    _, token = make_api_key(make_user("alice"))

    resp = _post(client, token, {"base_url": "https://cs.rutgers.edu/"})
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["url"] == "https://cs.rutgers.edu/"
    assert body["admin"] == "alice"
    website = db.session.get(Website, body["id"])
    assert website.domain.domain == "cs.rutgers.edu"


def test_create_queues_a_scan(client, make_user, make_api_key, monkeypatch):
    import scanner.tasks as tasks_mod

    queued = []
    monkeypatch.setattr(website_bp, "check_url", lambda url: True)
    monkeypatch.setattr(
        tasks_mod.scan_website, "delay",
        lambda url: queued.append(url) or types.SimpleNamespace(id="t-1"),
    )
    _domain("rutgers.edu")
    _, token = make_api_key(make_user())

    assert _post(client, token, {"base_url": "https://cs.rutgers.edu/"}).status_code == 201
    assert queued == ["https://cs.rutgers.edu/"]


def test_create_requires_a_json_object(client, make_user, make_api_key):
    _, token = make_api_key(make_user())
    headers = _key_header(token)

    resp = client.post("/api/v1/websites", data="not json", headers=headers)
    assert resp.status_code == 400
    resp = client.post("/api/v1/websites", json=["https://cs.rutgers.edu/"], headers=headers)
    assert resp.status_code == 400


def test_create_requires_base_url(client, make_user, make_api_key):
    _, token = make_api_key(make_user())
    resp = _post(client, token, {})
    assert resp.status_code == 400
    assert "Base URL" in resp.get_json()["error"]


def test_create_outside_allow_list_names_the_host(client, make_user, make_api_key, monkeypatch):
    from models import db
    from models.website import Domain

    monkeypatch.setattr(website_bp, "check_url", _never)
    _, token = make_api_key(make_user())

    resp = _post(client, token, {"base_url": "https://cs.rutgers.edu/"})
    assert resp.status_code == 400
    body = resp.get_json()
    assert body["code"] == "no_parent_domain"
    assert body["domain"] == "cs.rutgers.edu"
    assert db.session.query(Domain).count() == 0


def test_create_duplicate_is_rejected(client, make_user, make_api_key, created):
    _domain("rutgers.edu")
    _, token = make_api_key(make_user())

    assert _post(client, token, {"base_url": "https://cs.rutgers.edu/"}).status_code == 201
    resp = _post(client, token, {"base_url": "https://cs.rutgers.edu/"})
    assert resp.status_code == 400
    assert "already exists" in resp.get_json()["error"]


def test_create_unreachable_site_is_rejected(client, make_user, make_api_key, monkeypatch):
    from models import db
    from models.website import Website

    _domain("rutgers.edu")
    monkeypatch.setattr(website_bp, "check_url", lambda url: False)
    _, token = make_api_key(make_user())

    resp = _post(client, token, {"base_url": "https://cs.rutgers.edu/"})
    assert resp.status_code == 400
    assert db.session.query(Website).count() == 0


def test_admin_key_can_allow_list_pick_admin_and_categories(client, make_user, make_api_key, created):
    from models import db
    from models.website import Domain, Website

    make_user("bob")
    _, token = make_api_key(make_user("root", is_admin=True))

    resp = _post(client, token, {
        "base_url": "https://cs.rutgers.edu/",
        "create_domain": True,
        "admin": "bob",
        "categories": ["Research", " Lab ", ""],
    })
    assert resp.status_code == 201
    assert db.session.query(Domain).filter_by(domain="cs.rutgers.edu").one().active
    website = db.session.get(Website, resp.get_json()["id"])
    assert website.admin.username == "bob"
    assert website.get_categories() == ["Research", "Lab"]


def test_non_admin_key_cannot_use_admin_fields(client, make_user, make_api_key, created):
    from models import db
    from models.website import Website

    _domain("rutgers.edu")
    make_user("bob")
    _, token = make_api_key(make_user("alice"))

    resp = _post(client, token, {
        "base_url": "https://cs.rutgers.edu/", "admin": "bob", "categories": ["x"],
    })
    assert resp.status_code == 201
    website = db.session.get(Website, resp.get_json()["id"])
    assert website.admin.username == "alice"
    assert website.get_categories() == []

    resp = _post(client, token, {"base_url": "https://other.example/", "create_domain": True})
    assert resp.status_code == 400
    assert resp.get_json()["code"] == "no_parent_domain"

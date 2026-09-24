"""Tests for updating websites through the API-key surface (PATCH /api/v1/websites/<id>)."""
import pytest

import models.website as website_models


@pytest.fixture(autouse=True)
def _no_dns(monkeypatch):
    # Domain/Website validation resolves hostnames; keep these tests offline.
    monkeypatch.setattr(website_models, "is_valid_url", lambda url: True)


def _key_header(token):
    return {"X-API-Key": token}


def _patch(client, token, website_id, body):
    return client.patch(f"/api/v1/websites/{website_id}", json=body, headers=_key_header(token))


def test_update_requires_key(client, make_user, make_website):
    website = make_website(make_user())
    resp = client.patch(f"/api/v1/websites/{website.id}", json={"description": "x"})
    assert resp.status_code == 401


def test_update_unknown_website_is_not_found(client, make_user, make_api_key):
    _, token = make_api_key(make_user())
    assert _patch(client, token, 999999, {"description": "x"}).status_code == 404


def test_update_requires_a_json_object(client, make_user, make_api_key, make_website):
    user = make_user()
    website = make_website(user)
    _, token = make_api_key(user)
    headers = _key_header(token)

    resp = client.patch(f"/api/v1/websites/{website.id}", data="not json", headers=headers)
    assert resp.status_code == 400
    resp = client.patch(f"/api/v1/websites/{website.id}", json=["x"], headers=headers)
    assert resp.status_code == 400


def test_update_requires_edit_permission(client, make_user, make_api_key, make_website):
    from models import db

    owner = make_user("bob")
    member = make_user("carol")
    other = make_user("alice")
    website = make_website(owner, public=True)
    website.users.append(member)
    db.session.commit()

    for user in (member, other):
        _, token = make_api_key(user)
        resp = _patch(client, token, website.id, {"users": ["carol"]})
        assert resp.status_code == 403, user.username
        assert resp.get_json() == {"error": "Unauthorized"}


def test_website_admin_can_set_users_and_extra_start_urls(client, make_user, make_api_key, make_website):
    from models import db
    from models.website import Website

    owner = make_user("bob")
    make_user("carol")
    website = make_website(owner, base="https://example.com")
    _, token = make_api_key(owner)

    resp = _patch(client, token, website.id, {
        "users": ["carol"],
        "extra_start_urls": ["https://example.com/section/"],
    })
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["users"] == ["carol"]
    assert body["extra_start_urls"] == ["https://example.com/section/"]
    website = db.session.get(Website, website.id)
    assert [u.username for u in website.users] == ["carol"]


def test_extra_start_url_on_another_host_is_rejected(client, make_user, make_api_key, make_website):
    owner = make_user("bob")
    website = make_website(owner, base="https://example.com")
    _, token = make_api_key(owner)

    resp = _patch(client, token, website.id, {"extra_start_urls": ["https://other.example/"]})
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_website_admin_cannot_change_admin_only_fields(client, make_user, make_api_key, make_website):
    from models import db
    from models.website import Website

    owner = make_user("bob")
    website = make_website(owner)
    before = (website.description, website.public, website.rate_limit)
    _, token = make_api_key(owner)

    resp = _patch(client, token, website.id, {"description": "Main site", "public": True, "rate_limit": 1})
    assert resp.status_code == 200
    website = db.session.get(Website, website.id)
    assert (website.description, website.public, website.rate_limit) == before


def test_admin_key_can_update_description_and_settings(client, make_user, make_api_key, make_website):
    owner = make_user("bob")
    admin = make_user("root", is_admin=True)
    website = make_website(owner)
    _, token = make_api_key(admin)

    resp = _patch(client, token, website.id, {
        "description": "  Main site  ",
        "categories": ["Research", " Lab ", ""],
        "tags": "wcag2a, wcag2aa",
        "public": True,
        "rate_limit": 7,
        "should_email": False,
    })
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["description"] == "Main site"
    assert body["categories"] == ["Research", "Lab"]
    assert body["tags"] == ["wcag2a", "wcag2aa"]
    assert body["public"] is True
    assert body["rate_limit"] == 7
    assert body["should_email"] is False


def test_admin_key_can_change_the_website_admin(client, make_user, make_api_key, make_website):
    owner = make_user("bob")
    make_user("carol")
    admin = make_user("root", is_admin=True)
    website = make_website(owner)
    _, token = make_api_key(admin)

    resp = _patch(client, token, website.id, {"admin": "carol"})
    assert resp.status_code == 200
    assert resp.get_json()["admin"] == "carol"

    resp = _patch(client, token, website.id, {"admin": "carol"})
    assert resp.status_code == 400
    assert "already the admin" in resp.get_json()["error"]


def test_cannot_activate_under_an_inactive_domain(client, make_user, make_api_key, make_website):
    from models import db

    owner = make_user("bob")
    admin = make_user("root", is_admin=True)
    website = make_website(owner)
    website.active = False
    website.domain.active = False
    db.session.commit()
    _, token = make_api_key(admin)

    resp = _patch(client, token, website.id, {"active": True})
    assert resp.status_code == 400
    assert "domain is inactive" in resp.get_json()["error"]

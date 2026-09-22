"""Tests for the API-key website and domain search endpoints on /api/v1."""
import pytest

import models.website as website_models


@pytest.fixture(autouse=True)
def _no_dns(monkeypatch):
    # Domain/Website validation resolves hostnames; keep these tests offline.
    monkeypatch.setattr(website_models, "is_valid_url", lambda url: True)


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


# --- websites ---------------------------------------------------------------


def test_websites_requires_key(client):
    assert client.get("/api/v1/websites").status_code == 401


def test_websites_lists_only_visible(client, make_user, make_website, make_api_key):
    bob = make_user("bob")
    alice = make_user("alice")
    make_website(bob, base="https://private.example")
    public = make_website(bob, base="https://public.example", public=True)
    mine = make_website(alice, base="https://mine.example")
    _, token = make_api_key(alice)

    resp = client.get("/api/v1/websites", headers=_key_header(token))
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["count"] == 2
    # ordered by url
    assert [w["id"] for w in body["items"]] == [mine.id, public.id]


def test_websites_admin_sees_all(client, make_user, make_website, make_api_key):
    bob = make_user("bob")
    admin = make_user("root", is_admin=True)
    make_website(bob, base="https://private.example")
    make_website(bob, base="https://public.example", public=True)
    make_website(admin, base="https://admin.example")
    _, token = make_api_key(admin)

    body = client.get("/api/v1/websites", headers=_key_header(token)).get_json()
    assert body["count"] == 3


def test_websites_search_case_insensitive(client, make_user, make_website, make_api_key):
    user = make_user()
    site = make_website(user, base="https://example.com")
    make_website(user, base="https://other.org")
    _, token = make_api_key(user)
    headers = _key_header(token)

    body = client.get("/api/v1/websites", query_string={"search": "EXAMPLE"}, headers=headers).get_json()
    assert body["count"] == 1
    assert body["items"][0]["id"] == site.id
    body = client.get("/api/v1/websites", query_string={"search": "nomatch"}, headers=headers).get_json()
    assert body["count"] == 0


def test_websites_search_escapes_wildcards(client, make_user, make_website, make_api_key):
    user = make_user()
    make_website(user, base="https://axb.example.com")
    underscore = make_website(user, base="https://a_b.example.com")
    _, token = make_api_key(user)

    # A bare LIKE would treat "_" as a wildcard and match axb too.
    body = client.get("/api/v1/websites", query_string={"search": "a_b"}, headers=_key_header(token)).get_json()
    assert [w["id"] for w in body["items"]] == [underscore.id]


def test_websites_host_exact_and_normalised(client, make_user, make_website, make_api_key):
    user = make_user()
    site = make_website(user, base="https://www.cs.rutgers.edu")
    _, token = make_api_key(user)
    headers = _key_header(token)

    for value in ("WWW.CS.Rutgers.EDU.", "HTTPS://www.cs.rutgers.edu/p?q=1"):
        body = client.get("/api/v1/websites", query_string={"host": value}, headers=headers).get_json()
        assert body["count"] == 1, value
        assert body["items"][0]["id"] == site.id

    # exact host only: the parent domain does not match a www. website
    body = client.get("/api/v1/websites", query_string={"host": "cs.rutgers.edu"}, headers=headers).get_json()
    assert body["count"] == 0


def test_websites_host_respects_visibility(client, make_user, make_website, make_api_key):
    bob = make_user("bob")
    alice = make_user("alice")
    make_website(bob, base="https://private.example")
    _, token = make_api_key(alice)

    body = client.get(
        "/api/v1/websites", query_string={"host": "private.example"}, headers=_key_header(token)
    ).get_json()
    assert body["count"] == 0


def test_websites_host_blank_ignored_invalid_400(client, make_user, make_website, make_api_key):
    user = make_user()
    make_website(user, base="https://example.com")
    _, token = make_api_key(user)
    headers = _key_header(token)

    resp = client.get("/api/v1/websites", query_string={"host": ""}, headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()["count"] == 1

    for bad in ("https://", "https://[::1"):
        resp = client.get("/api/v1/websites", query_string={"host": bad}, headers=headers)
        assert resp.status_code == 400, bad
        assert "host" in resp.get_json()["error"]


def test_websites_pagination(client, make_user, make_website, make_api_key):
    user = make_user()
    for name in ("a", "b", "c"):
        make_website(user, base=f"https://{name}.example.com")
    _, token = make_api_key(user)
    headers = _key_header(token)

    def page(**params):
        resp = client.get("/api/v1/websites", query_string=params, headers=headers)
        return resp.status_code, resp.get_json()

    status, body = page(limit=2, page=1)
    assert status == 200
    assert body["count"] == 3
    assert len(body["items"]) == 2

    status, body = page(limit=2, page=2)
    assert status == 200
    assert len(body["items"]) == 1

    status, body = page(limit=2, page=9)
    assert status == 200
    assert body["count"] == 3
    assert body["items"] == []

    assert page(page=0)[0] == 400
    assert page(limit=0)[0] == 400


# --- domains ----------------------------------------------------------------


def test_domains_requires_admin_key(client, make_user, make_api_key):
    assert client.get("/api/v1/domains").status_code == 401

    _, token = make_api_key(make_user("alice"))
    resp = client.get("/api/v1/domains", headers=_key_header(token))
    assert resp.status_code == 403
    assert resp.get_json() == {"error": "Unauthorized"}


def test_domains_host_covering_most_specific_first(client, make_user, make_api_key):
    _domain("rutgers.edu")
    _domain("cs.rutgers.edu")
    _domain("njit.edu")
    _, token = make_api_key(make_user("root", is_admin=True))

    body = client.get(
        "/api/v1/domains", query_string={"host": "web.cs.rutgers.edu"}, headers=_key_header(token)
    ).get_json()
    assert body["count"] == 2
    assert [d["domain"] for d in body["items"]] == ["cs.rutgers.edu", "rutgers.edu"]


def test_domains_host_rejects_lookalike(client, make_user, make_api_key):
    _domain("rutgers.edu")
    _, token = make_api_key(make_user("root", is_admin=True))

    for host in ("evil-rutgers.edu", "rutgers.edu.evil.com"):
        body = client.get("/api/v1/domains", query_string={"host": host}, headers=_key_header(token)).get_json()
        assert body["count"] == 0, host


def test_domains_host_includes_inactive(client, make_user, make_api_key):
    _domain("rutgers.edu", active=False)
    _, token = make_api_key(make_user("root", is_admin=True))

    body = client.get(
        "/api/v1/domains", query_string={"host": "cs.rutgers.edu"}, headers=_key_header(token)
    ).get_json()
    assert body["count"] == 1
    assert body["items"][0]["domain"] == "rutgers.edu"
    assert body["items"][0]["active"] is False


def test_domains_search_and_host_combine(client, make_user, make_api_key):
    _domain("rutgers.edu")
    _domain("cs.rutgers.edu")
    _domain("njit.edu")
    _, token = make_api_key(make_user("root", is_admin=True))
    headers = _key_header(token)

    body = client.get("/api/v1/domains", query_string={"search": "RUT"}, headers=headers).get_json()
    assert [d["domain"] for d in body["items"]] == ["cs.rutgers.edu", "rutgers.edu"]

    body = client.get(
        "/api/v1/domains", query_string={"host": "web.cs.rutgers.edu", "search": "cs."}, headers=headers
    ).get_json()
    assert [d["domain"] for d in body["items"]] == ["cs.rutgers.edu"]


def test_domains_no_filter_lists_all(client, make_user, make_api_key):
    for name in ("rutgers.edu", "cs.rutgers.edu", "njit.edu"):
        _domain(name)
    _, token = make_api_key(make_user("root", is_admin=True))

    body = client.get("/api/v1/domains", headers=_key_header(token)).get_json()
    assert body["count"] == 3
    assert [d["domain"] for d in body["items"]] == ["cs.rutgers.edu", "njit.edu", "rutgers.edu"]

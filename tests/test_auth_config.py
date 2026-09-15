"""Tests for auth transport (header-only JWT), CORS scope, and startup config guards."""
import pytest


def _bearer(jwt_header, user):
    return jwt_header(user)["Authorization"].split(" ", 1)[1]


def test_jwt_is_not_accepted_from_cookie(client, make_user, jwt_header):
    user = make_user()
    client.set_cookie("access_token_cookie", _bearer(jwt_header, user))
    assert client.get("/api/users/me/").status_code == 401

    client.delete_cookie("access_token_cookie")
    assert client.get("/api/users/me/", headers=jwt_header(user)).status_code == 200


CAS_HEADERS = {"x-cas-user": "alice", "x-cas-server": "https://cas.rutgers.edu/cas"}


def test_cas_login_returns_token_in_body_only(client, app):
    resp = client.get(
        "/api/auth/cas",
        headers={**CAS_HEADERS, "X-Internal-Secret": app.config["INTERNAL_AUTH_SECRET"]},
    )
    assert resp.status_code == 200
    assert resp.get_json()["access_token"]
    assert "Set-Cookie" not in resp.headers


def test_cas_login_requires_internal_secret(client):
    from models import db
    from models.user import User

    assert client.get("/api/auth/cas", headers=CAS_HEADERS).status_code == 403
    assert (
        client.get("/api/auth/cas", headers={**CAS_HEADERS, "X-Internal-Secret": "wrong"}).status_code
        == 403
    )
    # No account is created for a rejected request.
    assert db.session.query(User).count() == 0


def test_cas_login_refused_when_secret_unconfigured(client, app):
    app.config["INTERNAL_AUTH_SECRET"] = ""
    resp = client.get("/api/auth/cas", headers={**CAS_HEADERS, "X-Internal-Secret": ""})
    assert resp.status_code == 403


def test_cas_login_grants_admin_only_for_full_email_match(client, app, monkeypatch):
    import authentication.permissions as permissions

    monkeypatch.setattr(permissions, "SITE_ADMINS", ["Alice@rutgers.edu"])
    secret = {"X-Internal-Secret": app.config["INTERNAL_AUTH_SECRET"]}

    # Same local part, different CAS server: not an admin.
    resp = client.get(
        "/api/auth/cas",
        headers={"x-cas-user": "alice", "x-cas-server": "https://cas.evil.example/cas", **secret},
    )
    assert resp.status_code == 200 and resp.get_json()["is_admin"] is False

    resp = client.get(
        "/api/auth/cas",
        headers={"x-cas-user": "bob", "x-cas-server": "https://cas.rutgers.edu/cas", **secret},
    )
    assert resp.status_code == 200 and resp.get_json()["is_admin"] is False

    resp = client.get(
        "/api/auth/cas",
        headers={"x-cas-user": "alice2", "x-cas-server": "https://cas.rutgers.edu/cas", **secret},
    )
    assert resp.status_code == 200 and resp.get_json()["is_admin"] is False


def test_is_site_admin_matches_full_email_case_insensitively(monkeypatch):
    import authentication.permissions as permissions

    monkeypatch.setattr(permissions, "SITE_ADMINS", ["Admin@Rutgers.edu", "  second@example.com "])
    assert permissions.is_site_admin("admin@rutgers.edu")
    assert permissions.is_site_admin("SECOND@example.com")
    assert not permissions.is_site_admin("admin@evil.com")
    assert not permissions.is_site_admin("admin")
    assert not permissions.is_site_admin("")
    assert not permissions.is_site_admin(None)


def test_cors_is_limited_to_client_url(client, app):
    preflight = {"Access-Control-Request-Method": "GET"}

    evil = client.options("/api/users/me/", headers={"Origin": "https://evil.example", **preflight})
    assert "Access-Control-Allow-Origin" not in evil.headers

    ok = client.options("/api/users/me/", headers={"Origin": app.config["CLIENT_URL"], **preflight})
    assert ok.headers.get("Access-Control-Allow-Origin") == app.config["CLIENT_URL"]
    assert "Access-Control-Allow-Credentials" not in ok.headers


def test_require_fails_fast_outside_testing(monkeypatch):
    import config

    monkeypatch.delenv("SOME_REQUIRED_SECRET", raising=False)
    monkeypatch.setenv("TESTING", "False")
    with pytest.raises(RuntimeError, match="SOME_REQUIRED_SECRET"):
        config._require("SOME_REQUIRED_SECRET")

    monkeypatch.setenv("TESTING", "True")
    assert config._require("SOME_REQUIRED_SECRET")  # placeholder under tests

    monkeypatch.setenv("SOME_REQUIRED_SECRET", "abc")
    assert config._require("SOME_REQUIRED_SECRET") == "abc"


def test_init_admin_skipped_without_credentials(app, monkeypatch):
    from app import init_admin
    from models import db
    from models.user import User

    monkeypatch.delenv("ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    init_admin(app)
    assert db.session.query(User).count() == 0


def test_init_admin_creates_admin_when_configured(app, monkeypatch):
    from app import init_admin
    from models import db
    from models.user import User

    monkeypatch.setenv("ADMIN_EMAIL", "root@example.com")
    monkeypatch.setenv("ADMIN_PASSWORD", "s3cret")
    init_admin(app)
    user = db.session.query(User).filter_by(email="root@example.com").one()
    assert user.profile.is_admin

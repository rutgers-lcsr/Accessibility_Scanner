"""Tests for the public, API-key-authenticated /api/v1 surface."""
from datetime import datetime, timedelta, timezone


def _key_header(token):
    return {"X-API-Key": token}


# --- authentication ---------------------------------------------------------


def test_missing_key_is_unauthorized(client, make_user, make_site, add_report):
    user = make_user()
    site = make_site(user)
    report = add_report(site)
    resp = client.get(f"/api/v1/reports/{report.id}")
    assert resp.status_code == 401


def test_invalid_key_is_unauthorized(client, make_user, make_site, add_report):
    user = make_user()
    report = add_report(make_site(user))
    resp = client.get(f"/api/v1/reports/{report.id}", headers=_key_header("a11y_nope"))
    assert resp.status_code == 401


def test_revoked_key_is_unauthorized(client, make_user, make_site, add_report, make_api_key):
    from models import db

    user = make_user()
    report = add_report(make_site(user))
    api_key, token = make_api_key(user)
    api_key.revoked = True
    db.session.commit()
    resp = client.get(f"/api/v1/reports/{report.id}", headers=_key_header(token))
    assert resp.status_code == 401


def test_bearer_fallback_works(client, make_user, make_site, add_report, make_api_key):
    user = make_user()
    report = add_report(make_site(user))
    _, token = make_api_key(user)
    resp = client.get(
        f"/api/v1/reports/{report.id}", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200


def test_using_a_key_updates_last_used(client, make_user, make_site, add_report, make_api_key):
    user = make_user()
    report = add_report(make_site(user))
    api_key, token = make_api_key(user)
    assert api_key.last_used_at is None
    client.get(f"/api/v1/reports/{report.id}", headers=_key_header(token))
    assert api_key.last_used_at is not None


# --- formats ----------------------------------------------------------------


def test_json_is_default(client, make_user, make_site, add_report, make_api_key):
    user = make_user()
    report = add_report(make_site(user))
    _, token = make_api_key(user)
    resp = client.get(f"/api/v1/reports/{report.id}", headers=_key_header(token))
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["id"] == report.id
    assert "report_counts" in body


def test_markdown_format(client, make_user, make_site, add_report, make_api_key):
    user = make_user()
    report = add_report(make_site(user))
    _, token = make_api_key(user)
    resp = client.get(
        f"/api/v1/reports/{report.id}?format=markdown", headers=_key_header(token)
    )
    assert resp.status_code == 200
    assert resp.mimetype == "text/markdown"
    text = resp.get_data(as_text=True)
    assert "# Accessibility Report" in text
    assert "color-contrast" in text


def test_agent_format(client, make_user, make_site, add_report, make_api_key):
    user = make_user()
    report = add_report(make_site(user))
    _, token = make_api_key(user)
    resp = client.get(
        f"/api/v1/reports/{report.id}?format=agent", headers=_key_header(token)
    )
    assert resp.status_code == 200
    assert resp.mimetype == "text/markdown"
    text = resp.get_data(as_text=True)
    assert "Please fix" in text
    assert "color-contrast" in text


def test_pdf_format(client, make_user, make_site, add_report, make_api_key):
    user = make_user()
    report = add_report(make_site(user))
    _, token = make_api_key(user)
    resp = client.get(
        f"/api/v1/reports/{report.id}?format=pdf", headers=_key_header(token)
    )
    assert resp.status_code == 200
    assert resp.mimetype == "application/pdf"
    assert resp.get_data()[:4] == b"%PDF"


def test_unknown_format_is_bad_request(client, make_user, make_site, add_report, make_api_key):
    user = make_user()
    report = add_report(make_site(user))
    _, token = make_api_key(user)
    resp = client.get(
        f"/api/v1/reports/{report.id}?format=xml", headers=_key_header(token)
    )
    assert resp.status_code == 400


# --- lookup variants --------------------------------------------------------


def test_missing_report_is_not_found(client, make_user, make_api_key):
    user = make_user()
    _, token = make_api_key(user)
    resp = client.get("/api/v1/reports/999999", headers=_key_header(token))
    assert resp.status_code == 404


def test_latest_by_site(client, make_user, make_site, add_report, make_api_key):
    user = make_user()
    site = make_site(user)
    now = datetime.now(timezone.utc)
    add_report(site, when=now - timedelta(days=2))
    newest = add_report(site, when=now)
    _, token = make_api_key(user)
    resp = client.get(
        f"/api/v1/sites/{site.id}/reports/latest", headers=_key_header(token)
    )
    assert resp.status_code == 200
    assert resp.get_json()["id"] == newest.id


def test_latest_by_site_missing_site(client, make_user, make_api_key):
    user = make_user()
    _, token = make_api_key(user)
    resp = client.get("/api/v1/sites/999999/reports/latest", headers=_key_header(token))
    assert resp.status_code == 404


def test_latest_by_site_no_reports(client, make_user, make_site, make_api_key):
    user = make_user()
    site = make_site(user)
    _, token = make_api_key(user)
    resp = client.get(
        f"/api/v1/sites/{site.id}/reports/latest", headers=_key_header(token)
    )
    assert resp.status_code == 404


def test_latest_by_url(client, make_user, make_site, add_report, make_api_key):
    user = make_user()
    site = make_site(user)
    now = datetime.now(timezone.utc)
    add_report(site, when=now - timedelta(days=1))
    newest = add_report(site, when=now)
    _, token = make_api_key(user)
    resp = client.get(
        f"/api/v1/reports/latest?url={site.url}", headers=_key_header(token)
    )
    assert resp.status_code == 200
    assert resp.get_json()["id"] == newest.id


def test_latest_by_url_requires_url(client, make_user, make_api_key):
    user = make_user()
    _, token = make_api_key(user)
    resp = client.get("/api/v1/reports/latest", headers=_key_header(token))
    assert resp.status_code == 400


def test_latest_by_url_not_found(client, make_user, make_api_key):
    user = make_user()
    _, token = make_api_key(user)
    resp = client.get(
        "/api/v1/reports/latest?url=https://nope.example/x", headers=_key_header(token)
    )
    assert resp.status_code == 404


# --- permissions ------------------------------------------------------------


def test_cannot_view_other_users_private_report(
    client, make_user, make_site, add_report, make_api_key
):
    owner = make_user("bob")
    other = make_user("alice")
    report = add_report(make_site(owner, public=False))
    _, token = make_api_key(other)
    resp = client.get(f"/api/v1/reports/{report.id}", headers=_key_header(token))
    assert resp.status_code == 403


def test_can_view_public_report(client, make_user, make_site, add_report, make_api_key):
    owner = make_user("bob")
    other = make_user("alice")
    report = add_report(make_site(owner, public=True))
    _, token = make_api_key(other)
    resp = client.get(f"/api/v1/reports/{report.id}", headers=_key_header(token))
    assert resp.status_code == 200


def test_admin_can_view_any_report(client, make_user, make_site, add_report, make_api_key):
    owner = make_user("bob")
    admin = make_user("carol", is_admin=True)
    report = add_report(make_site(owner, public=False))
    _, token = make_api_key(admin)
    resp = client.get(f"/api/v1/reports/{report.id}", headers=_key_header(token))
    assert resp.status_code == 200


# --- swagger docs -----------------------------------------------------------


def test_swagger_spec_lists_only_public_api(client):
    resp = client.get("/api/apispec_1.json")
    assert resp.status_code == 200
    spec = resp.get_json()
    assert "ApiKeyAuth" in spec["securityDefinitions"]
    assert set(spec["paths"]) == {
        "/api/v1/reports/{report_id}",
        "/api/v1/reports/latest",
        "/api/v1/sites/{site_id}/reports/latest",
    }


def test_swagger_ui_served_under_api(client):
    resp = client.get("/api/docs/")
    assert resp.status_code == 200
    assert resp.mimetype == "text/html"

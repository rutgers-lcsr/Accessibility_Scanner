"""Tests for the JWT-protected key-management endpoints (/api/users/me/api-keys)."""

BASE = "/api/users/me/api-keys/"


def test_requires_authentication(client):
    assert client.get(BASE).status_code == 401


def test_list_is_empty_initially(client, make_user, jwt_header):
    user = make_user()
    resp = client.get(BASE, headers=jwt_header(user))
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_create_returns_plaintext_key_once(client, make_user, jwt_header):
    user = make_user()
    resp = client.post(BASE, headers=jwt_header(user), json={"name": "ci"})
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["name"] == "ci"
    assert body["key"].startswith("a11y_")
    assert body["prefix"] and body["key"].startswith(body["prefix"])

    # The secret is never returned again by the list endpoint.
    listed = client.get(BASE, headers=jwt_header(user)).get_json()
    assert len(listed) == 1
    assert "key" not in listed[0]


def test_create_requires_name(client, make_user, jwt_header):
    user = make_user()
    resp = client.post(BASE, headers=jwt_header(user), json={})
    assert resp.status_code == 400


def test_revoke_removes_key_from_list(client, make_user, jwt_header):
    user = make_user()
    created = client.post(BASE, headers=jwt_header(user), json={"name": "ci"}).get_json()
    resp = client.delete(f"{BASE}{created['id']}/", headers=jwt_header(user))
    assert resp.status_code == 200
    assert client.get(BASE, headers=jwt_header(user)).get_json() == []


def test_cannot_revoke_another_users_key(client, make_user, jwt_header):
    alice = make_user("alice")
    bob = make_user("bob")
    created = client.post(BASE, headers=jwt_header(alice), json={"name": "ci"}).get_json()
    resp = client.delete(f"{BASE}{created['id']}/", headers=jwt_header(bob))
    assert resp.status_code == 404


def test_created_key_can_be_used_against_public_api(
    client, make_user, jwt_header, make_site, add_report
):
    user = make_user()
    report = add_report(make_site(user))
    created = client.post(BASE, headers=jwt_header(user), json={"name": "ci"}).get_json()
    resp = client.get(
        f"/api/v1/reports/{report.id}", headers={"X-API-Key": created["key"]}
    )
    assert resp.status_code == 200
    assert resp.get_json()["id"] == report.id


def test_revoked_key_stops_working(client, make_user, jwt_header, make_site, add_report):
    user = make_user()
    report = add_report(make_site(user))
    created = client.post(BASE, headers=jwt_header(user), json={"name": "ci"}).get_json()
    token = created["key"]
    client.delete(f"{BASE}{created['id']}/", headers=jwt_header(user))
    resp = client.get(f"/api/v1/reports/{report.id}", headers={"X-API-Key": token})
    assert resp.status_code == 401

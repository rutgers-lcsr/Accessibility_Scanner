"""The single-report endpoint is the contract the frontend preview proxy relies on:
it must expose the report's url and script token to viewers and nothing to others."""


def test_report_visible_to_viewers_only(client, make_user, make_site, add_report, jwt_header):
    owner = make_user("bob")
    other = make_user("alice")
    site = make_site(owner)
    report = add_report(site)
    url = f"/api/reports/{report.id}/"

    assert client.get(url).status_code == 403  # anonymous, private website
    assert client.get(url, headers=jwt_header(other)).status_code == 403

    resp = client.get(url, headers=jwt_header(owner))
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["id"] == report.id
    assert body["url"] == report.url
    assert body["script_token"]


def test_public_report_is_readable_anonymously(client, make_user, make_site, add_report):
    site = make_site(make_user(), public=True)
    report = add_report(site)
    resp = client.get(f"/api/reports/{report.id}/")
    assert resp.status_code == 200
    assert resp.get_json()["url"] == report.url


def test_missing_report_is_404(client, make_user, jwt_header):
    assert client.get("/api/reports/999999/", headers=jwt_header(make_user())).status_code == 404

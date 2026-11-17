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


def test_report_names_the_websites_the_viewer_can_open(client, make_user, make_site, add_report, jwt_header):
    """The report page links back to its website ("All issues on ..."), so the API says
    which of the page's websites this viewer may open."""
    owner = make_user("bob")
    site = make_site(owner)
    report = add_report(site)
    website = site.websites.first()

    body = client.get(f"/api/reports/{report.id}/", headers=jwt_header(owner)).get_json()
    assert body["websites"] == [{"id": website.id, "url": website.url}]


def test_older_report_points_to_the_latest(client, make_user, make_site, add_report, jwt_header):
    """Statuses live on a page's latest report; an older one says which that is."""
    from datetime import datetime, timedelta, timezone

    owner = make_user("bob")
    site = make_site(owner)
    now = datetime.now(timezone.utc)
    old = add_report(site, when=now - timedelta(days=3))
    new = add_report(site, when=now)

    body = client.get(f"/api/reports/{old.id}/", headers=jwt_header(owner)).get_json()
    assert body["latest_report_id"] == new.id
    body = client.get(f"/api/reports/{new.id}/", headers=jwt_header(owner)).get_json()
    assert body["latest_report_id"] == new.id


def test_older_report_says_what_the_latest_scan_found(client, make_user, make_site, add_report, jwt_header):
    from datetime import datetime, timedelta, timezone

    owner = make_user("bob")
    site = make_site(owner)
    now = datetime.now(timezone.utc)
    old = add_report(site, when=now - timedelta(days=3))
    new = add_report(site, when=now, violations=[])

    body = client.get(f"/api/reports/{old.id}/", headers=jwt_header(owner)).get_json()
    assert body["latest_report"]["id"] == new.id
    assert body["latest_report"]["failing_rules"] == 0
    assert "latest_report" not in client.get(f"/api/reports/{new.id}/", headers=jwt_header(owner)).get_json()

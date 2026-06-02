"""Tests for the website-keyed endpoints (aggregate + latest page)."""
from datetime import datetime, timedelta, timezone


def _key_header(token):
    return {"X-API-Key": token}


def _website_with_two_pages(make_website, add_site, add_report, owner, public=False):
    website = make_website(owner, public=public)
    site_a = add_site(website, page="/a")
    site_b = add_site(website, page="/b")
    add_report(site_a)
    add_report(site_b)
    return website


# --- aggregate report -------------------------------------------------------


def test_aggregate_json_combines_pages(
    client, make_user, make_website, add_site, add_report, make_api_key
):
    user = make_user()
    website = _website_with_two_pages(make_website, add_site, add_report, user)
    _, token = make_api_key(user)

    resp = client.get(f"/api/v1/websites/{website.id}/report", headers=_key_header(token))
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["website_id"] == website.id
    assert "report_counts" in body
    violations = body["report"]["violations"]
    # same rule on both pages -> one entry listing both affected pages
    assert len(violations) == 1
    assert len(violations[0]["reports"]) == 2


def test_aggregate_agent_lists_affected_pages(
    client, make_user, make_website, add_site, add_report, make_api_key
):
    user = make_user()
    website = _website_with_two_pages(make_website, add_site, add_report, user)
    _, token = make_api_key(user)

    resp = client.get(
        f"/api/v1/websites/{website.id}/report?format=agent", headers=_key_header(token)
    )
    assert resp.status_code == 200
    assert resp.mimetype == "text/markdown"
    text = resp.get_data(as_text=True)
    assert "Please fix" in text
    assert "Affected pages (2)" in text


def test_aggregate_markdown(
    client, make_user, make_website, add_site, add_report, make_api_key
):
    user = make_user()
    website = _website_with_two_pages(make_website, add_site, add_report, user)
    _, token = make_api_key(user)

    resp = client.get(
        f"/api/v1/websites/{website.id}/report?format=markdown", headers=_key_header(token)
    )
    assert resp.status_code == 200
    assert resp.mimetype == "text/markdown"
    assert "# Accessibility Report for" in resp.get_data(as_text=True)


def test_aggregate_pdf_is_unsupported(
    client, make_user, make_website, add_site, add_report, make_api_key
):
    user = make_user()
    website = _website_with_two_pages(make_website, add_site, add_report, user)
    _, token = make_api_key(user)

    resp = client.get(
        f"/api/v1/websites/{website.id}/report?format=pdf", headers=_key_header(token)
    )
    assert resp.status_code == 400


def test_aggregate_missing_website(client, make_user, make_api_key):
    user = make_user()
    _, token = make_api_key(user)
    resp = client.get("/api/v1/websites/999999/report", headers=_key_header(token))
    assert resp.status_code == 404


def test_aggregate_forbidden_for_other_users_private_website(
    client, make_user, make_website, add_site, add_report, make_api_key
):
    owner = make_user("bob")
    other = make_user("alice")
    website = _website_with_two_pages(make_website, add_site, add_report, owner, public=False)
    _, token = make_api_key(other)
    resp = client.get(f"/api/v1/websites/{website.id}/report", headers=_key_header(token))
    assert resp.status_code == 403


# --- latest page for a website ---------------------------------------------


def test_latest_by_website_returns_latest_report_per_page(
    client, make_user, make_website, add_site, add_report, make_api_key
):
    user = make_user()
    website = make_website(user)
    site_a = add_site(website, page="/a")
    site_b = add_site(website, page="/b")
    now = datetime.now(timezone.utc)
    # each page has an old and a newer report
    add_report(site_a, when=now - timedelta(days=3))
    newest_a = add_report(site_a, when=now - timedelta(days=1))
    add_report(site_b, when=now - timedelta(days=2))
    newest_b = add_report(site_b, when=now)
    _, token = make_api_key(user)

    resp = client.get(
        f"/api/v1/websites/{website.id}/reports/latest", headers=_key_header(token)
    )
    assert resp.status_code == 200
    body = resp.get_json()
    # one report per page, each being that page's newest
    returned_ids = {r["id"] for r in body["reports"]}
    assert returned_ids == {newest_a.id, newest_b.id}


def test_latest_by_website_agent_covers_all_pages(
    client, make_user, make_website, add_site, add_report, make_api_key
):
    user = make_user()
    website = make_website(user)
    add_report(add_site(website, page="/a"))
    add_report(add_site(website, page="/b"))
    _, token = make_api_key(user)

    resp = client.get(
        f"/api/v1/websites/{website.id}/reports/latest?format=agent",
        headers=_key_header(token),
    )
    assert resp.status_code == 200
    text = resp.get_data(as_text=True)
    # one agent section per page
    assert text.count("# Accessibility Violations Report") == 2
    assert "example.com/a" in text and "example.com/b" in text


def test_latest_by_website_agent_skips_pages_without_violations(
    client, make_user, make_website, add_site, add_report, make_api_key
):
    user = make_user()
    website = make_website(user)
    add_report(add_site(website, page="/a"))  # has a violation
    add_report(add_site(website, page="/b"), violations=[])  # clean page
    _, token = make_api_key(user)

    resp = client.get(
        f"/api/v1/websites/{website.id}/reports/latest?format=agent",
        headers=_key_header(token),
    )
    assert resp.status_code == 200
    text = resp.get_data(as_text=True)
    # only the page with violations is included
    assert text.count("# Accessibility Violations Report") == 1
    assert "example.com/a" in text
    assert "example.com/b" not in text


def test_latest_by_website_missing_website(client, make_user, make_api_key):
    user = make_user()
    _, token = make_api_key(user)
    resp = client.get("/api/v1/websites/999999/reports/latest", headers=_key_header(token))
    assert resp.status_code == 404


def test_latest_by_website_no_reports(
    client, make_user, make_website, add_site, make_api_key
):
    user = make_user()
    website = make_website(user)
    add_site(website, page="/a")
    _, token = make_api_key(user)
    resp = client.get(
        f"/api/v1/websites/{website.id}/reports/latest", headers=_key_header(token)
    )
    assert resp.status_code == 404

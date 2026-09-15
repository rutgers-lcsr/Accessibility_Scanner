"""Failed scans are recorded on the website and page rows instead of vanishing into the
worker log, and pages that have never been audited successfully do not break anything."""
import asyncio
import types
from datetime import datetime, timezone

import pytest

import models.website as website_models
import scanner.scan as scan_mod


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    # Site/Website creation resolves hostnames; keep these tests offline.
    monkeypatch.setattr(website_models, "is_valid_url", lambda url: True)


def _proxy(website):
    """What the crawler hands to the store functions: just id and url."""
    return types.SimpleNamespace(id=website.id, url=website.url)


def _full_report(url):
    return {
        "url": url,
        "base_url": "https://example.com",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "report": {"violations": [], "incomplete": [], "inaccessible": [], "passes": []},
        "links": [],
        "videos": [],
        "imgs": [],
        "tabable": True,
        "photo": None,
        "tags": ["wcag2a"],
    }


# --- pages without a successful report ---------------------------------------------


def test_site_without_reports_has_no_current_report(app, make_user, make_site):
    site = make_site(make_user())
    assert site.get_recent_report() is None
    data = site.to_dict()
    assert data["current_report"] is None
    assert data["last_scan_status"] is None
    assert data["last_scan_error"] is None


def test_website_counts_tolerate_a_page_without_reports(app, make_user, make_site):
    website = make_site(make_user()).websites.first()
    counts = website.get_report_counts()
    assert counts["violations"]["total"] == 0
    data = website.to_dict()
    assert data["last_scan_status"] is None


def test_site_status_endpoint_for_page_without_reports(client, make_user, make_site, jwt_header):
    user = make_user()
    site = make_site(user)
    resp = client.get(f"/api/scans/status/?site={site.id}", headers=jwt_header(user))
    assert resp.status_code == 200
    assert resp.get_json() is None


def test_sites_listing_includes_pages_without_reports(
    client, make_user, make_website, add_site, add_report, jwt_header
):
    from models import db

    user = make_user()
    website = make_website(user)
    audited = add_site(website, page="/audited")
    add_report(audited)
    failed = add_site(website, page="/failed")
    failed.last_scan_status = "failed"
    failed.last_scan_error = "net::ERR_TIMED_OUT"
    db.session.commit()

    resp = client.get(f"/api/websites/{website.id}/sites/?limit=10", headers=jwt_header(user))
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["count"] == 2
    by_url = {item["url"]: item for item in body["items"]}
    assert by_url[audited.url]["current_report"] is not None
    assert by_url[failed.url]["current_report"] is None
    assert by_url[failed.url]["last_scan_status"] == "failed"
    assert by_url[failed.url]["last_scan_error"] == "net::ERR_TIMED_OUT"


# --- recording failures -------------------------------------------------------------


def test_page_failure_is_recorded_on_the_site(app, make_user, make_site):
    from models import db

    site = make_site(make_user())
    website = site.websites.first()

    asyncio.run(
        scan_mod.store_failure_to_db(
            {"url": site.url, "error": "net::ERR_TIMED_OUT", "timestamp": "2026-01-01T00:00:00Z"},
            _proxy(website),
            app,
        )
    )

    db.session.expire_all()
    site = db.session.get(website_models.Site, site.id)
    assert site.last_scan_status == "failed"
    assert "ERR_TIMED_OUT" in site.last_scan_error
    assert site.scanning is False
    assert site.get_recent_report() is None  # no report row was written


def test_page_failure_creates_the_site_when_it_is_new(app, make_user, make_website):
    from models import db

    website = make_website(make_user())
    url = website.url + "/broken"

    asyncio.run(scan_mod.store_failure_to_db({"url": url, "error": "503"}, _proxy(website), app))

    db.session.expire_all()
    site = db.session.query(website_models.Site).filter_by(url=url).first()
    assert site is not None
    assert site.last_scan_status == "failed"
    assert site in db.session.get(website_models.Website, website.id).sites.all()


def test_page_failure_off_site_is_ignored(app, make_user, make_website):
    from models import db

    website = make_website(make_user())
    asyncio.run(
        scan_mod.store_failure_to_db({"url": "https://other.example/x", "error": "x"}, _proxy(website), app)
    )
    db.session.expire_all()
    assert db.session.query(website_models.Site).filter_by(url="https://other.example/x").first() is None


def test_successful_store_clears_an_earlier_failure(app, make_user, make_site):
    from models import db

    site = make_site(make_user())
    website = site.websites.first()
    site.last_scan_status = "failed"
    site.last_scan_error = "earlier"
    db.session.commit()

    asyncio.run(scan_mod.store_report_to_db(_full_report(site.url), _proxy(website), app))

    db.session.expire_all()
    site = db.session.get(website_models.Site, site.id)
    assert site.last_scan_status == "completed"
    assert site.last_scan_error is None
    assert site.get_recent_report() is not None


def test_unreachable_website_is_recorded_and_task_cleared(app, make_user, make_website, monkeypatch):
    from models import db

    website = make_website(make_user())
    monkeypatch.setattr(scan_mod, "check_url", lambda url: False)

    results = asyncio.run(scan_mod.generate_reports(website.url, task_id="t-1"))

    assert results == []
    db.session.expire_all()
    website = db.session.get(website_models.Website, website.id)
    assert website.last_scan_status == "unreachable"
    assert website.last_scan_error
    assert website.current_task_id is None

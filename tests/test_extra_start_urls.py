"""Websites whose sections are not linked from the root: extra start pages are stored on
the website, validated against its host, and seed the crawl alongside the root."""
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


# --- model ----------------------------------------------------------------------------


def test_start_urls_are_normalised_and_deduplicated(app, make_user, make_website):
    website = make_website(make_user())
    website.set_extra_start_urls([
        " https://Example.COM/cs440-fa26/#syllabus ",
        "https://example.com/cs440-fa26/",
        "https://example.com/",  # the root is always crawled; not stored twice
        "",
    ])
    assert website.get_extra_start_urls() == ["https://example.com/cs440-fa26/"]
    assert website.to_dict()["extra_start_urls"] == ["https://example.com/cs440-fa26/"]

    website.set_extra_start_urls([])
    assert website.get_extra_start_urls() == []


@pytest.mark.parametrize(
    "bad",
    [
        "https://other.example.com/x",  # another host
        "https://example.com:8443/x",  # another port
        "cs440-fa26/",  # relative
        "ftp://example.com/x",  # not http(s)
    ],
)
def test_start_urls_must_be_pages_of_the_website(app, make_user, make_website, bad):
    website = make_website(make_user())
    with pytest.raises(ValueError):
        website.set_extra_start_urls([bad])
    assert website.get_extra_start_urls() == []


# --- API ------------------------------------------------------------------------------


def test_owner_can_set_and_clear_start_urls(client, make_user, make_website, jwt_header):
    owner = make_user()
    website = make_website(owner)

    resp = client.patch(
        f"/api/websites/{website.id}/",
        json={"extra_start_urls": ["https://example.com/a/", "https://example.com/b"]},
        headers=jwt_header(owner),
    )
    assert resp.status_code == 200
    assert resp.get_json()["extra_start_urls"] == ["https://example.com/a/", "https://example.com/b"]

    resp = client.patch(
        f"/api/websites/{website.id}/", json={"extra_start_urls": []}, headers=jwt_header(owner)
    )
    assert resp.status_code == 200
    assert resp.get_json()["extra_start_urls"] == []


def test_start_urls_off_the_website_are_rejected(client, make_user, make_website, jwt_header):
    owner = make_user()
    website = make_website(owner)

    resp = client.patch(
        f"/api/websites/{website.id}/",
        json={"extra_start_urls": ["https://evil.example/x"]},
        headers=jwt_header(owner),
    )
    assert resp.status_code == 400
    assert "example.com" in resp.get_json()["error"]

    resp = client.patch(
        f"/api/websites/{website.id}/", json={"extra_start_urls": 5}, headers=jwt_header(owner)
    )
    assert resp.status_code == 400


def test_start_urls_need_edit_permission(client, make_user, make_website, jwt_header):
    owner = make_user("alice")
    viewer = make_user("bob")
    website = make_website(owner, public=True)

    resp = client.patch(
        f"/api/websites/{website.id}/",
        json={"extra_start_urls": ["https://example.com/a/"]},
        headers=jwt_header(viewer),
    )
    assert resp.status_code == 403


# --- crawler --------------------------------------------------------------------------


def test_crawl_is_seeded_with_the_root_and_every_start_url(app, make_user, make_website):
    website = make_website(make_user())
    website.set_extra_start_urls(["https://example.com/cs440-fa26/", "https://example.com/cs440-fa26"])
    assert scan_mod.crawl_start_urls(website) == [
        "https://example.com/",
        "https://example.com/cs440-fa26/",
        "https://example.com/cs440-fa26",
    ]


class _FakePlaywright:
    """Enough of async_playwright() for generate_reports: a browser that can be closed."""

    async def __aenter__(self):
        async def launch(**kwargs):
            return types.SimpleNamespace(close=self._close)

        return types.SimpleNamespace(chromium=types.SimpleNamespace(launch=launch))

    async def __aexit__(self, *exc):
        return False

    async def _close(self):
        pass


def _fake_site(pages):
    """generate_report stand-in backed by a {url: [links]} map."""

    async def fake(browser, website, tags, ace_config):
        return {
            "url": website,
            "base_url": "https://example.com",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "report": {"violations": [], "incomplete": [], "inaccessible": [], "passes": []},
            "links": pages[website],
            "videos": [],
            "imgs": [],
            "tabable": True,
            "photo": None,
            "tags": ["wcag2a"],
        }

    return fake


def test_full_scan_audits_sections_not_linked_from_the_root(app, make_user, make_website, monkeypatch):
    from models import db

    # The root only links to /about; the course site under /cs440-fa26/ is an island.
    pages = {
        "https://example.com/": ["https://example.com/about"],
        "https://example.com/about": [],
        "https://example.com/cs440-fa26/": ["https://example.com/cs440-fa26/lectures"],
        "https://example.com/cs440-fa26/lectures": [],
    }
    website = make_website(make_user())
    website.set_extra_start_urls(["https://example.com/cs440-fa26/"])
    db.session.commit()

    monkeypatch.setattr(scan_mod, "check_url", lambda url: True)
    monkeypatch.setattr(scan_mod, "load_robots", lambda url: None)
    monkeypatch.setattr(scan_mod, "async_playwright", _FakePlaywright)
    monkeypatch.setattr(scan_mod, "generate_report", _fake_site(pages))

    results = asyncio.run(scan_mod.generate_reports(website.url, task_id="t-1"))

    assert {r.url for r in results} == set(pages)
    db.session.expire_all()
    website = db.session.get(website_models.Website, website.id)
    assert {site.url for site in website.sites} == set(pages)
    assert website.last_scan_status == "completed"


def test_without_the_start_url_the_island_is_not_found(app, make_user, make_website, monkeypatch):
    """Control for the test above: the same site with no extra start page."""
    from models import db

    pages = {
        "https://example.com/": ["https://example.com/about"],
        "https://example.com/about": [],
        "https://example.com/cs440-fa26/": [],
    }
    website = make_website(make_user())

    monkeypatch.setattr(scan_mod, "check_url", lambda url: True)
    monkeypatch.setattr(scan_mod, "load_robots", lambda url: None)
    monkeypatch.setattr(scan_mod, "async_playwright", _FakePlaywright)
    monkeypatch.setattr(scan_mod, "generate_report", _fake_site(pages))

    results = asyncio.run(scan_mod.generate_reports(website.url, task_id="t-1"))

    assert {r.url for r in results} == {"https://example.com/", "https://example.com/about"}
    db.session.expire_all()
    website = db.session.get(website_models.Website, website.id)
    assert {site.url for site in website.sites} == {"https://example.com/", "https://example.com/about"}

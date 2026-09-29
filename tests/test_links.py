"""Broken-link check: collection during the crawl, the inventory, the probe, the
per-scan check and the listing endpoint."""
import asyncio
from datetime import datetime, timedelta, timezone
from urllib import robotparser

import pytest

import models.website as website_models
from models import db
import scanner.scan as scan_mod
import services.links as links_mod
from models.link import Link, LinkSource
from scanner.utils.queue import ListQueue
from services.links import check_website_links, fetch_link, sync_links


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setattr(website_models, "is_valid_url", lambda url: True)


# --- collection --------------------------------------------------------------------------------


def test_crawler_collects_link_targets_from_every_host(monkeypatch):
    async def fake(browser, website, tags, ace_config):
        return {"url": website, "timestamp": "2026-01-01T00:00:00Z", "report": {"violations": []}, "links": [],
                "link_targets": [{"href": "https://example.com/about", "text": "About"},
                                 {"href": "https://other.org/", "text": ""}]}

    monkeypatch.setattr(scan_mod, "generate_report", fake)
    link_targets = {}

    async def run():
        queue = ListQueue()
        await queue.put("https://example.com/")
        done, processing, results = set(), set(), []
        worker = asyncio.create_task(scan_mod.process_website(
            name=0, ace_config="", tags=[], browser=None, queue=queue, results=results, sites_done=done,
            currently_processing=processing, limits={"max_pages": 10, "max_depth": 5, "crawl_delay": 0},
            depths={"https://example.com/": 0}, link_targets=link_targets,
        ))
        await queue.join()
        await queue.put(None)
        await worker
        return done

    assert asyncio.run(run()) == {"https://example.com/"}
    assert link_targets == {
        "https://example.com/about": {"https://example.com/": "About"},
        "https://other.org/": {"https://example.com/": ""},
    }


# --- inventory ---------------------------------------------------------------------------------


def test_sync_creates_updates_and_removes_links(app, make_user, make_website, add_site):
    from models import db

    website = make_website(make_user())
    home = add_site(website, page="/")
    about = add_site(website, page="/about")
    first = sync_links(website.id, {
        "https://example.com/contact": {home.url: "Contact", about.url: "Contact us"},
        "https://other.org/": {home.url: "Partner"},
        "https://gone.example/": {home.url: ""},
    })
    assert first == {"new": 3, "updated": 0, "removed": 0}
    by_url = {link.url: link for link in db.session.query(Link).all()}
    assert by_url["https://example.com/contact"].external is False and by_url["https://example.com/contact"].status == "pending"
    assert by_url["https://other.org/"].external is True
    assert [(s["url"], s["text"]) for s in by_url["https://example.com/contact"].to_dict()["found_on"]] == [
        (home.url, "Contact"), (about.url, "Contact us")]
    assert [s["text"] for s in by_url["https://gone.example/"].to_dict()["found_on"]] == [None]

    by_url["https://other.org/"].status, by_url["https://other.org/"].status_code = "broken", 404
    db.session.commit()
    second = sync_links(website.id, {
        "https://example.com/contact": {home.url: "Contact (new)"},
        "https://other.org/": {home.url: "Partner"},
    })
    assert second == {"new": 0, "updated": 2, "removed": 1}
    assert db.session.query(Link).filter_by(url="https://gone.example/").count() == 0
    contact = db.session.query(Link).filter_by(url="https://example.com/contact").one()
    assert [(s["url"], s["text"]) for s in contact.to_dict()["found_on"]] == [(home.url, "Contact (new)")]
    other = db.session.query(Link).filter_by(url="https://other.org/").one()
    assert other.status == "broken" and other.status_code == 404  # results survive a re-sync
    assert db.session.query(LinkSource).count() == 2


def test_sync_skips_overlong_urls_and_folds_case(app, make_user, make_website, add_site):
    from models import db

    website = make_website(make_user())
    home = add_site(website, page="/")
    about = add_site(website, page="/about")
    result = sync_links(website.id, {
        "https://example.com/Contact": {home.url: "Contact"},
        "https://example.com/contact": {about.url: "contact"},
        "https://example.com/" + "x" * 1000: {home.url: "long"},
    })
    assert result == {"new": 1, "updated": 0, "removed": 0}
    link = db.session.query(Link).one()
    assert link.url == "https://example.com/Contact"
    assert sorted(s["url"] for s in link.to_dict()["found_on"]) == [home.url, about.url]

    # a re-sync spelled the other way updates the same row instead of inserting a twin
    assert sync_links(website.id, {"https://example.com/contact": {home.url: "c"}}) == {"new": 0, "updated": 1, "removed": 0}
    assert db.session.query(Link).count() == 1


# --- probe -------------------------------------------------------------------------------------


class _Resp:
    def __init__(self, status=200, location=None):
        self.status_code = status
        self.headers = {"Location": location} if location is not None else {}
        self.is_redirect = status in (301, 302, 303, 307, 308) and location is not None
        self.is_permanent_redirect = status in (301, 308) and location is not None

    def close(self):
        pass


def test_fetch_link_maps_statuses_falls_back_to_get_and_guards_redirects(monkeypatch):
    calls = []
    table = {
        "/ok": _Resp(200), "/missing": _Resp(404), "/login": _Resp(403), "/down": _Resp(503),
        "/moved": _Resp(301, location="/ok"), "/loop": _Resp(302, location="/loop"),
        "/internal": _Resp(302, location="https://10.0.0.1/secret"), "/nowhere": _Resp(302, location=""),
        "/headless": _Resp(301), "/far": _Resp(302, location="/" + "y" * 1200), "/" + "y" * 1200: _Resp(200),
    }

    def fake_head(url, **kwargs):
        calls.append(("HEAD", url))
        if url.endswith("/head-rejected"):
            return _Resp(405)
        return table[url.replace("https://example.com", "")]

    def fake_get(url, **kwargs):
        calls.append(("GET", url))
        if url.endswith("/head-rejected"):
            return _Resp(200)
        return table[url.replace("https://example.com", "")]

    monkeypatch.setattr(links_mod.requests, "head", fake_head)
    monkeypatch.setattr(links_mod.requests, "get", fake_get)
    monkeypatch.setattr(links_mod, "is_safe_target", lambda url: not url.startswith("https://10.") and "nonexistent" not in url)
    monkeypatch.setattr(links_mod, "_host_resolves", lambda url: "nonexistent" not in url)

    assert fetch_link("https://example.com/ok") == ("ok", 200, None, None)
    assert fetch_link("https://example.com/missing") == ("broken", 404, None, "HTTP 404")
    assert fetch_link("https://example.com/login") == ("blocked", 403, None, "HTTP 403")
    assert fetch_link("https://example.com/down") == ("error", 503, None, "HTTP 503")
    assert fetch_link("https://example.com/head-rejected") == ("ok", 200, None, None)
    assert ("GET", "https://example.com/head-rejected") in calls
    assert fetch_link("https://example.com/moved") == ("ok", 200, "https://example.com/ok", None)
    assert fetch_link("https://example.com/loop")[0::3] == ("error", "Too many redirects")
    status, _, _, error = fetch_link("https://example.com/internal")
    assert status == "skipped" and "non-public" in error
    assert not any(url.startswith("https://10.") for _, url in calls)
    assert fetch_link("https://example.com/nowhere")[0::3] == ("error", "Redirect without a location")
    assert fetch_link("https://nonexistent.invalid/") == ("error", None, None, "DNS lookup failed")
    # a 3xx with no Location header at all is not a working link either
    assert fetch_link("https://example.com/headless")[0::3] == ("error", "Redirect without a location")
    # a redirect target wider than the column is cut to fit
    status, code, final_url, _ = fetch_link("https://example.com/far")
    assert (status, code, len(final_url)) == ("ok", 200, 1000)
    # a GET is only sent when HEAD did not answer
    assert calls.count(("GET", "https://example.com/ok")) == 0 and calls.count(("GET", "https://example.com/missing")) == 1

    def boom(url, **kwargs):
        raise ConnectionError("refused")

    monkeypatch.setattr(links_mod.requests, "head", boom)
    assert fetch_link("https://example.com/ok") == ("error", None, None, "ConnectionError: refused")


# --- the check ---------------------------------------------------------------------------------


def test_check_respects_cap_robots_recheck_window_and_off(app, make_user, make_website, add_site, monkeypatch):
    from models import db
    from models.settings import Settings

    website = make_website(make_user())
    home = add_site(website, page="/")
    sync_links(website.id, {
        "https://example.com/a": {home.url: "a"},
        "https://example.com/private/b": {home.url: "b"},
        "https://elsewhere.org/private/c": {home.url: "c"},
        "https://example.com/d": {home.url: "d"},
    })
    Settings.set("link_checks_per_scan", "3")  # robots-skipped links do not count
    probed = []

    def fake_fetch(url):
        probed.append(url)
        return ("broken", 404, None, "HTTP 404") if url.endswith("/a") else ("ok", 200, None, None)

    monkeypatch.setattr(links_mod, "fetch_link", fake_fetch)
    robots = robotparser.RobotFileParser()
    robots.parse(["User-agent: *", "Disallow: /private/"])

    assert check_website_links(website.id, robots=robots) == 3
    by_url = {link.url: link for link in db.session.query(Link).all()}
    assert by_url["https://example.com/a"].status == "broken" and by_url["https://example.com/a"].status_code == 404
    assert by_url["https://example.com/private/b"].status == "skipped" and by_url["https://example.com/private/b"].checked_at
    assert by_url["https://elsewhere.org/private/c"].status == "ok"  # robots.txt covers the website's host only
    assert by_url["https://example.com/d"].status == "ok"
    # off-site targets are queued before same-site ones
    assert probed[0] == "https://elsewhere.org/private/c"
    assert sorted(probed) == ["https://elsewhere.org/private/c", "https://example.com/a", "https://example.com/d"]
    assert website.get_link_counts() == {"total": 4, "broken": 1}

    # a second run within the recheck window checks nothing
    assert check_website_links(website.id) == 0
    by_url["https://example.com/a"].checked_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=10)
    db.session.commit()
    assert check_website_links(website.id) == 1

    Settings.set("link_checks_per_scan", "0")
    by_url["https://example.com/a"].checked_at = None
    db.session.commit()
    assert check_website_links(website.id) == 0


# --- endpoint ----------------------------------------------------------------------------------


def test_links_endpoint_visibility_order_and_filters(client, make_user, make_website, add_site, jwt_header):
    from models import db

    owner = make_user("alice")
    website = make_website(owner)
    home = add_site(website, page="/")
    sync_links(website.id, {
        "https://example.com/z": {home.url: "z"},
        "https://example.com/a": {home.url: "a"},
        "https://other.org/b": {home.url: "b"},
    })
    db.session.query(Link).filter_by(url="https://other.org/b").one().status = "broken"
    db.session.query(Link).filter_by(url="https://example.com/a").one().status = "ok"
    db.session.commit()

    url = f"/api/websites/{website.id}/links/"
    assert client.get(url).status_code == 403
    assert client.get(url, headers=jwt_header(make_user("carol"))).status_code == 403
    body = client.get(url, headers=jwt_header(owner)).get_json()
    assert body["count"] == 3
    assert [l["url"] for l in body["items"]] == ["https://other.org/b", "https://example.com/z", "https://example.com/a"]
    assert body["items"][0]["found_on"] == [{"url": home.url, "text": "b", "site_id": home.id, "report_id": None}]
    assert body["items"][0]["external"] is True
    assert client.get(url + "?status=broken", headers=jwt_header(owner)).get_json()["count"] == 1
    assert client.get(url + "?external=false", headers=jwt_header(owner)).get_json()["count"] == 2
    assert client.get(url + "?status=nope", headers=jwt_header(owner)).status_code == 400
    site = client.get(f"/api/websites/{website.id}/", headers=jwt_header(owner)).get_json()
    assert site["link_counts"] == {"total": 3, "broken": 1}
    website.public = True
    assert client.get(url).status_code == 200


def test_site_links_endpoint_lists_the_pages_links_broken_first(client, make_user, make_website, add_site, add_report, jwt_header):
    from models import db

    owner = make_user("alice")
    website = make_website(owner)
    home = add_site(website, page="/")
    about = add_site(website, page="/about")
    report = add_report(home)
    sync_links(website.id, {
        "https://example.com/z": {home.url: "z link"},
        "https://other.org/b": {home.url: "b link", about.url: "b elsewhere"},
        "https://example.com/only-about": {about.url: "not on home"},
    })
    db.session.query(Link).filter_by(url="https://other.org/b").one().status = "broken"
    db.session.commit()

    url = f"/api/sites/{home.id}/links/"
    assert client.get(url).status_code == 403
    assert client.get(url, headers=jwt_header(make_user("carol"))).status_code == 403
    body = client.get(url, headers=jwt_header(owner)).get_json()
    assert [(l["url"], l["text"], l["status"]) for l in body["items"]] == [
        ("https://other.org/b", "b link", "broken"), ("https://example.com/z", "z link", "pending")]
    assert client.get(f"/api/sites/999999/links/", headers=jwt_header(owner)).status_code == 404

    # the website listing links each source page to its latest report
    body = client.get(f"/api/websites/{website.id}/links/?status=broken", headers=jwt_header(owner)).get_json()
    by_site = {s["site_id"]: s["report_id"] for s in body["items"][0]["found_on"]}
    assert by_site == {home.id: report.id, about.id: None}


def test_website_delete_removes_links(app, make_user, make_website, add_site):
    from models import db

    website = make_website(make_user())
    home = add_site(website, page="/")
    sync_links(website.id, {"https://example.com/a": {home.url: "a"}})
    website.delete()
    db.session.commit()
    assert db.session.query(Link).count() == 0 and db.session.query(LinkSource).count() == 0


# --- dashboard and emails ----------------------------------------------------------------------


def test_broken_link_counts_reach_the_dashboard_and_the_emails(client, make_user, make_website, add_site, add_report, jwt_header):
    from mail.emails import AdminDigestEmail, OwnerDigestEmail
    from services.overview import build_digest
    from services.owner_digest import build_owner_digest

    admin = make_user("root", is_admin=True)
    website = make_website(admin)
    home = add_site(website, page="/")
    add_report(home, violations=[{"id": "region", "impact": "serious", "help": "Fix region", "helpUrl": "https://x/region",
                                  "nodes": [{"target": ["#a"], "html": "<p>a</p>"}]}])
    sync_links(website.id, {
        "https://example.com/a": {home.url: "a"},
        "https://other.org/b": {home.url: "b"},
        "https://other.org/c": {home.url: "c"},
    })
    for url in ("https://other.org/b", "https://other.org/c"):
        db.session.query(Link).filter_by(url=url).one().status = "broken"
    db.session.commit()

    dashboard = client.get("/api/dashboard/", headers=jwt_header(admin)).get_json()
    assert dashboard["totals"]["broken_links"] == 2 and dashboard["websites"][0]["broken_links"] == 2

    digest = build_owner_digest(admin, [website], None)
    assert digest["websites"][0]["broken_links"] == 2 and digest["totals"]["broken_links"] == 2
    email = OwnerDigestEmail(admin, digest, tone="first")
    assert email.send()
    assert f"2 broken links (links to pages that no longer exist): http://localhost:3000/websites/{website.id}?tab=links" in email.msg.body
    assert f"/websites/{website.id}?tab=links" in email.msg.html and "2 broken links" in email.msg.html

    assert build_digest(7)["totals"]["broken_links"] == 2
    weekly = AdminDigestEmail()
    assert weekly.send()
    assert "2 broken links across all websites" in weekly.msg.html

    # nothing about links when none are broken
    db.session.query(Link).update({"status": "ok"})
    db.session.commit()
    email = OwnerDigestEmail(admin, build_owner_digest(admin, [website], None), tone="first")
    assert email.send() and "broken link" not in email.msg.body and "broken link" not in email.msg.html

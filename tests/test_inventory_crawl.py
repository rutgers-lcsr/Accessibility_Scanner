"""Crawl inventories: the in-page collector (run in a real browser when one is
installed), stale and mixed content per page, media and third-party syncs, the
endpoints and the vendor register."""
from datetime import datetime, timedelta

import pytest

import models.website as website_models
from models import db
from models.inventory import MediaItem, ThirdPartyHost, Vendor, match_vendor
from services.inventory import (collect_page_inventory, content_hash, media_counts, page_content_counts,
                                sync_media, sync_third_parties, unassigned_hosts, update_page_content)


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setattr(website_models, "is_valid_url", lambda url: True)


PAGE = """<!doctype html><html><head>
<script src="https://cdn.vendor.example/widget.js"></script>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter">
<link rel="stylesheet" href="/local.css">
<script src="http://insecure.example/old.js"></script>
</head><body>
<header>Site nav that is not main content</header>
<main>
  <h1>Welcome</h1><p>Main content.</p>
  <video src="/media/intro.mp4"><track kind="captions" src="/media/intro.vtt"></video>
  <video src="https://cdn.site.test/talk.mp4"></video>
  <audio src="/media/podcast.mp3"></audio>
  <iframe src="https://www.youtube.com/embed/abc123?rel=0"></iframe>
  <iframe src="https://other.example/map"></iframe>
  <img src="http://insecure.example/logo.png" alt="">
  <form action="https://forms.vendor.example/submit"></form>
</main></body></html>"""


def test_inventory_js_in_a_real_browser():
    sync_api = pytest.importorskip("playwright.sync_api")
    from scanner.browser.parse import get_inventory_js

    try:
        with sync_api.sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            try:
                page = browser.new_page()
                page.route("**/*", lambda route: route.fulfill(status=200, content_type="text/html", body=PAGE)
                           if route.request.url.startswith("https://site.test/") else route.abort())
                page.goto("https://site.test/")
                found = page.evaluate(get_inventory_js())
            finally:
                browser.close()
    except Exception as e:  # no browser binary installed
        pytest.skip(f"Chromium unavailable: {e}")

    media = {m["url"]: m for m in found["media"]}
    assert media["https://site.test/media/intro.mp4"]["captions"] == "present"
    assert media["https://cdn.site.test/talk.mp4"]["captions"] == "missing"
    assert media["https://site.test/media/podcast.mp3"]["kind"] == "audio"
    assert media["https://site.test/media/podcast.mp3"]["captions"] == "unknown"
    youtube = media["https://www.youtube.com/embed/abc123?rel=0"]
    assert (youtube["kind"], youtube["provider"], youtube["captions"]) == ("embed", "youtube", "unknown")
    assert "https://other.example/map" not in media  # not a known player

    hosts = {(t["host"], t["kind"]) for t in found["third_party"]}
    assert ("cdn.vendor.example", "script") in hosts
    assert ("fonts.googleapis.com", "stylesheet") in hosts
    assert ("other.example", "iframe") in hosts
    assert ("forms.vendor.example", "form") in hosts
    assert not any(host == "site.test" for host, _ in hosts)

    mixed = {(m["url"], m["tag"]) for m in found["mixed_content"]}
    assert ("http://insecure.example/old.js", "script") in mixed
    assert ("http://insecure.example/logo.png", "img") in mixed

    assert "Main content." in found["text"]
    assert "Site nav" not in found["text"]


# --- per page ---------------------------------------------------------------------------------


def test_content_hash_ignores_whitespace():
    assert content_hash("Hello   world\n") == content_hash("Hello world")
    assert content_hash("Hello world") != content_hash("Hello there")
    assert content_hash("") is None and content_hash(None) is None


def test_update_page_content_tracks_changes(app, make_user, make_site):
    site = make_site(make_user())
    t0 = datetime(2026, 1, 1)
    update_page_content(site, {"content_text": "v1", "mixed_content": [{"url": "http://x/a.js", "tag": "script"}]}, t0)
    assert site.content_changed_at == t0 and site.mixed_content == [{"url": "http://x/a.js", "tag": "script"}]

    update_page_content(site, {"content_text": "v1  "}, t0 + timedelta(days=30))
    assert site.content_changed_at == t0  # same text
    assert site.mixed_content == []

    t2 = t0 + timedelta(days=60)
    update_page_content(site, {"content_text": "v2"}, t2)
    assert site.content_changed_at == t2


def test_first_scan_uses_last_modified(app, make_user, make_site):
    site = make_site(make_user())
    update_page_content(site, {"content_text": "old page", "last_modified": "Wed, 21 Oct 2020 07:28:00 GMT"},
                        datetime(2026, 11, 1))
    assert site.content_changed_at == datetime(2020, 10, 21, 7, 28)
    assert site.last_modified == datetime(2020, 10, 21, 7, 28)


def test_page_content_counts(app, make_user, make_website, add_site):
    from models.settings import Settings
    Settings.set("stale_after_days", "100")
    website = make_website(make_user())
    now = datetime(2026, 11, 17)
    fresh, stale, mixed = add_site(website, "/fresh"), add_site(website, "/stale"), add_site(website, "/mixed")
    fresh.content_changed_at = now - timedelta(days=5)
    stale.content_changed_at = now - timedelta(days=200)
    mixed.content_changed_at = now - timedelta(days=50)
    mixed.mixed_content = [{"url": "http://x", "tag": "img"}]
    db.session.commit()
    counts = page_content_counts([website.id], now)[website.id]
    assert counts == {"stale_pages": 1, "mixed_content_pages": 1, "last_change": now - timedelta(days=5)}


# --- crawl-wide ---------------------------------------------------------------------------------


def _report(media=(), third_party=()):
    return {"media": list(media), "third_party": list(third_party)}


def test_collect_merges_pages_and_captions():
    media, tp = {}, {}
    video = {"url": "https://e.com/v.mp4", "kind": "video", "provider": "html5", "captions": "missing"}
    collect_page_inventory(media, tp, "https://e.com/a", _report([video], [{"url": "https://cdn.x/a.js", "host": "cdn.x", "kind": "script"}]))
    collect_page_inventory(media, tp, "https://e.com/b", _report([{**video, "captions": "present"}],
                                                               [{"url": "https://cdn.x/b.css", "host": "cdn.x", "kind": "stylesheet"}]))
    assert media["https://e.com/v.mp4"]["captions"] == "present"
    assert media["https://e.com/v.mp4"]["pages"] == {"https://e.com/a", "https://e.com/b"}
    assert tp["cdn.x"]["kinds"] == {"script", "stylesheet"} and len(tp["cdn.x"]["pages"]) == 2


def test_sync_media_keeps_verdicts_and_removes_gone(app, make_user, make_website, add_site):
    website = make_website(make_user())
    home = add_site(website, "/")
    found = {
        "https://www.youtube.com/embed/a": {"kind": "embed", "provider": "youtube", "captions": "unknown",
                                            "audio_description": False, "pages": {home.url}},
        "https://example.com/gone.mp4": {"kind": "video", "provider": "html5", "captions": "missing",
                                         "audio_description": False, "pages": {home.url}},
    }
    assert sync_media(website.id, found) == {"new": 2, "updated": 0, "removed": 0}
    embed = db.session.query(MediaItem).filter_by(url="https://www.youtube.com/embed/a").one()
    embed.caption_override = "verified"
    db.session.commit()
    assert media_counts([website.id])[website.id] == {"total": 2, "missing": 1, "unknown": 0}

    del found["https://example.com/gone.mp4"]
    assert sync_media(website.id, found) == {"new": 0, "updated": 1, "removed": 1}
    embed = db.session.query(MediaItem).one()
    assert embed.caption_override == "verified" and embed.caption_status == "present"
    assert embed.to_dict()["pages"] == [home.url]


def test_sync_third_parties_skips_own_host(app, make_user, make_website):
    website = make_website(make_user())
    found = {"cdn.x": {"kinds": {"script"}, "example_url": "https://cdn.x/a.js", "pages": {"https://example.com/"}},
             "example.com": {"kinds": {"script"}, "example_url": "https://example.com/a.js", "pages": {"https://example.com/"}}}
    assert sync_third_parties(website.id, found)["new"] == 1
    assert [row.host for row in db.session.query(ThirdPartyHost).all()] == ["cdn.x"]
    assert sync_third_parties(website.id, {})["removed"] == 1


def test_crawl_collects_and_syncs_inventories(app, make_user, make_website, monkeypatch):
    """A full (faked) crawl stores page content and syncs media and third parties."""
    import asyncio
    import scanner.scan as scan_mod

    class _FakeBrowser:
        async def close(self):
            pass

    class _FakeChromium:
        async def launch(self, **kwargs):
            return _FakeBrowser()

    class _FakePlaywright:
        def __init__(self):
            self.chromium = _FakeChromium()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

    async def fake(browser, website, tags, ace_config):
        return {"url": website, "timestamp": "2026-01-01T00:00:00+00:00", "report": {"violations": []},
                "links": [], "videos": [], "imgs": [], "tabable": True, "photo": None,
                "media": [{"url": "https://www.youtube.com/embed/x", "kind": "embed", "provider": "youtube", "captions": "unknown"}],
                "third_party": [{"url": "https://cdn.x/a.js", "host": "cdn.x", "kind": "script"}],
                "mixed_content": [{"url": "http://x/a.png", "tag": "img"}], "content_text": "hello"}

    website = make_website(make_user())
    monkeypatch.setattr(scan_mod, "check_url", lambda url: True)
    monkeypatch.setattr(scan_mod, "load_robots", lambda url: None)
    monkeypatch.setattr(scan_mod, "async_playwright", _FakePlaywright)
    monkeypatch.setattr(scan_mod, "generate_report", fake)
    import services.links as links_mod
    monkeypatch.setattr(links_mod, "check_website_links", lambda *a, **k: 0)

    asyncio.run(scan_mod.generate_reports(website.url, task_id="t-1"))

    db.session.expire_all()
    site = website.sites.first()
    assert site.content_hash == content_hash("hello") and site.mixed_content == [{"url": "http://x/a.png", "tag": "img"}]
    assert [m.url for m in db.session.query(MediaItem).all()] == ["https://www.youtube.com/embed/x"]
    assert [t.host for t in db.session.query(ThirdPartyHost).all()] == ["cdn.x"]


# --- vendors ---------------------------------------------------------------------------------------


def test_match_vendor_prefers_most_specific():
    google = Vendor(id=1, name="Google", hosts="google.com\ngoogleapis.com")
    fonts = Vendor(id=2, name="Google Fonts", hosts="fonts.googleapis.com")
    assert match_vendor("fonts.googleapis.com", [google, fonts]) is fonts
    assert match_vendor("maps.googleapis.com", [google, fonts]) is google
    assert match_vendor("notgoogle.com", [google, fonts]) is None


def test_vendor_api_and_unassigned_hosts(client, jwt_header, make_user, make_website):
    admin, owner = make_user("root", is_admin=True), make_user("owner")
    website = make_website(owner)
    now = datetime(2026, 11, 1)
    for host in ("cdn.kaltura.com", "www.googletagmanager.com"):
        db.session.add(ThirdPartyHost(website_id=website.id, host=host, kinds="script", page_count=3,
                                      first_seen=now, last_seen=now))
    db.session.commit()
    assert [h["host"] for h in unassigned_hosts()] == ["cdn.kaltura.com", "www.googletagmanager.com"]
    sites = unassigned_hosts()[0]["sites"]
    assert sites == [{"website_id": website.id, "url": website.url, "pages": 3, "kinds": ["script"], "example_pages": []}]

    body = {"name": "Kaltura", "hosts": ["kaltura.com"], "status": "approved",
            "vpat_url": "https://example.com/kaltura-acr.pdf", "vpat_date": "2026-03-01", "review_due": "2020-01-01"}
    assert client.post("/api/vendors/", json=body, headers=jwt_header(owner)).status_code == 403
    resp = client.post("/api/vendors/", json=body, headers=jwt_header(admin))
    assert resp.status_code == 201, resp.get_json()
    vendor = resp.get_json()
    assert vendor["hosts"] == ["kaltura.com"] and vendor["review_overdue"] is True

    assert client.post("/api/vendors/", json={**body, "hosts": ["not a host"]}, headers=jwt_header(admin)).status_code == 400
    assert client.post("/api/vendors/", json={**body, "status": "maybe"}, headers=jwt_header(admin)).status_code == 400
    assert client.post("/api/vendors/", json={**body, "vpat_url": "ftp://x"}, headers=jwt_header(admin)).status_code == 400

    listed = client.get("/api/vendors/", headers=jwt_header(owner)).get_json()
    assert listed[0]["websites"] == 1
    assert listed[0]["sites"] == [{"website_id": website.id, "url": website.url, "hosts": ["cdn.kaltura.com"],
                                   "pages": 3, "kinds": ["script"]}]
    # Someone who cannot see the website gets the count, not its name.
    hidden = client.get("/api/vendors/", headers=jwt_header(make_user("stranger"))).get_json()
    assert hidden[0]["websites"] == 1 and hidden[0]["sites"] == []
    assert [h["host"] for h in client.get("/api/vendors/unassigned-hosts/", headers=jwt_header(admin)).get_json()] == [
        "www.googletagmanager.com"]

    rows = client.get(f"/api/websites/{website.id}/third-parties/", headers=jwt_header(owner)).get_json()
    assert [(r["host"], r["vendor"] and r["vendor"]["name"]) for r in rows] == [
        ("www.googletagmanager.com", None), ("cdn.kaltura.com", "Kaltura")]

    resp = client.patch(f"/api/vendors/{vendor['id']}/", json={"review_due": "2099-01-01"}, headers=jwt_header(admin))
    assert resp.get_json()["review_overdue"] is False
    assert client.delete(f"/api/vendors/{vendor['id']}/", headers=jwt_header(admin)).status_code == 204


# --- endpoints -------------------------------------------------------------------------------------


def test_media_endpoint_filter_and_override(client, jwt_header, make_user, make_website, add_site):
    owner, stranger = make_user("owner"), make_user("stranger")
    website = make_website(owner, public=True)
    home = add_site(website, "/")
    sync_media(website.id, {
        "https://example.com/a.mp4": {"kind": "video", "provider": "html5", "captions": "missing",
                                      "audio_description": False, "pages": {home.url}},
        "https://www.youtube.com/embed/a": {"kind": "embed", "provider": "youtube", "captions": "unknown",
                                            "audio_description": False, "pages": {home.url}},
    })
    body = client.get(f"/api/websites/{website.id}/media/").get_json()
    assert [i["caption_status"] for i in body["items"]] == ["missing", "unknown"]
    embed_id = body["items"][1]["id"]

    url = f"/api/websites/{website.id}/media/{embed_id}/"
    assert client.patch(url, json={"caption_override": "verified"}, headers=jwt_header(stranger)).status_code == 403
    assert client.patch(url, json={"caption_override": "yes"}, headers=jwt_header(owner)).status_code == 400
    resp = client.patch(url, json={"caption_override": "verified", "note": "Checked the CC button"}, headers=jwt_header(owner))
    assert resp.get_json()["caption_status"] == "present" and resp.get_json()["override_by"] == "owner"
    assert client.get(f"/api/websites/{website.id}/media/?status=unknown").get_json()["count"] == 0
    assert client.get(f"/api/websites/{website.id}/").get_json()["media_counts"] == {"total": 2, "missing": 1, "unknown": 0}


def test_content_endpoint_filters(client, jwt_header, make_user, make_website, add_site):
    owner = make_user("owner")
    website = make_website(owner)
    old, new, mixed = add_site(website, "/old"), add_site(website, "/new"), add_site(website, "/mixed")
    old.content_changed_at = datetime(2020, 1, 1)
    new.content_changed_at = datetime.utcnow()
    mixed.content_changed_at = datetime.utcnow()
    mixed.mixed_content = [{"url": "http://x/a.png", "tag": "img"}]
    new.mixed_content = []
    db.session.commit()
    headers = jwt_header(owner)
    body = client.get(f"/api/websites/{website.id}/content/", headers=headers).get_json()
    assert body["count"] == 3 and body["items"][0]["url"].endswith("/old") and body["items"][0]["stale"] is True
    stale = client.get(f"/api/websites/{website.id}/content/?filter=stale", headers=headers).get_json()
    assert [i["url"] for i in stale["items"]] == [old.url]
    mixed_rows = client.get(f"/api/websites/{website.id}/content/?filter=mixed", headers=headers).get_json()
    assert [i["url"] for i in mixed_rows["items"]] == [mixed.url]
    assert client.get(f"/api/websites/{website.id}/content/?filter=nope", headers=headers).status_code == 400


def test_deleting_a_website_removes_its_inventories(app, make_user, make_website, add_site):
    website = make_website(make_user())
    home = add_site(website, "/")
    sync_media(website.id, {"https://example.com/a.mp4": {"kind": "video", "provider": "html5", "captions": "missing",
                                                           "audio_description": False, "pages": {home.url}}})
    sync_third_parties(website.id, {"cdn.x": {"kinds": {"script"}, "example_url": None, "pages": {home.url}}})
    website.delete()
    assert db.session.query(MediaItem).count() == 0 and db.session.query(ThirdPartyHost).count() == 0

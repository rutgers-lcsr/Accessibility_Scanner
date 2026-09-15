"""Crawler safety: URL normalisation, the page/depth budget, politeness delay, robots.txt,
and race-safe Site creation."""
import asyncio
import types

import pytest

import scanner.scan as scan_mod
from scanner.utils.queue import ListQueue
from utils.urls import normalize_url


# --- normalize_url ----------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("https://Example.COM/About", "https://example.com/About"),
        ("https://example.com/docs#intro", "https://example.com/docs"),
        ("https://example.com/list?page=2", "https://example.com/list"),
        ("HTTPS://example.com:443/", "https://example.com/"),
        ("http://example.com:80/x", "http://example.com/x"),
        ("http://example.com:8080/x", "http://example.com:8080/x"),
        ("https://example.com", "https://example.com/"),
        ("https://example.com/about/", "https://example.com/about/"),  # path kept as-is
        ("  https://example.com/a  ", "https://example.com/a"),
    ],
)
def test_normalize_url(raw, expected):
    assert normalize_url(raw) == expected


# --- crawl budget ------------------------------------------------------------------


def _fake_tree(fanout=3):
    """generate_report stand-in: every page links to `fanout` children under its path."""

    async def fake(browser, website, tags, ace_config):
        base = website.rstrip("/")
        return {
            "url": website,
            "timestamp": "2026-01-01T00:00:00Z",
            "report": {"violations": []},
            "links": [f"{base}/{i}" for i in range(fanout)],
        }

    return fake


def _crawl(limits, robots=None):
    async def run():
        root = "https://example.com/"
        queue = ListQueue()
        await queue.put(root)
        sites_done, processing, results = set(), set(), []
        worker = asyncio.create_task(
            scan_mod.process_website(
                name=0,
                ace_config="",
                tags=[],
                browser=None,
                queue=queue,
                results=results,
                sites_done=sites_done,
                currently_processing=processing,
                limits=limits,
                depths={root: 0},
                robots=robots,
            )
        )
        await queue.join()
        await queue.put(None)
        await worker
        return sites_done, results

    return asyncio.run(run())


def test_depth_limit_bounds_the_crawl(monkeypatch):
    monkeypatch.setattr(scan_mod, "generate_report", _fake_tree(3))
    done, _ = _crawl({"max_pages": 10_000, "max_depth": 1, "crawl_delay": 0})
    # root + its 3 children; the children's links are depth 2 and are not queued
    assert done == {"https://example.com/", "https://example.com/0", "https://example.com/1", "https://example.com/2"}


def test_page_budget_bounds_the_crawl(monkeypatch):
    monkeypatch.setattr(scan_mod, "generate_report", _fake_tree(3))
    done, _ = _crawl({"max_pages": 5, "max_depth": 50, "crawl_delay": 0})
    assert len(done) == 5


def test_depth_zero_scans_only_the_start_page(monkeypatch):
    monkeypatch.setattr(scan_mod, "generate_report", _fake_tree(3))
    done, results = _crawl({"max_pages": 100, "max_depth": 0, "crawl_delay": 0})
    assert done == {"https://example.com/"}
    assert len(results) == 1


def test_crawl_delay_is_applied(monkeypatch):
    monkeypatch.setattr(scan_mod, "generate_report", _fake_tree(0))
    sleeps = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    monkeypatch.setattr(scan_mod.asyncio, "sleep", fake_sleep)
    _crawl({"max_pages": 100, "max_depth": 5, "crawl_delay": 0.25})
    assert sleeps == [0.25]


# --- robots.txt --------------------------------------------------------------------


class _Resp:
    def __init__(self, status, text=""):
        self.status_code = status
        self.text = text


def test_robots_disallow_is_honoured(monkeypatch):
    robots_txt = "User-agent: *\nDisallow: /private/\n\nUser-agent: LCSRAccessibility\nDisallow: /internal/\n"
    monkeypatch.setattr(scan_mod.requests, "get", lambda url, **kw: _Resp(200, robots_txt))
    robots = scan_mod.load_robots("https://example.com/some/page")

    assert robots is not None
    assert robots.can_fetch(scan_mod.ROBOTS_AGENT, "https://example.com/public/") is True
    assert robots.can_fetch(scan_mod.ROBOTS_AGENT, "https://example.com/internal/x") is False

    monkeypatch.setattr(scan_mod, "generate_report", _fake_tree(0))
    done, results = _crawl({"max_pages": 100, "max_depth": 5, "crawl_delay": 0}, robots=robots)
    assert done == {"https://example.com/"} and len(results) == 1


def test_disallowed_pages_are_skipped_without_a_request(monkeypatch):
    robots_txt = "User-agent: *\nDisallow: /\n"
    monkeypatch.setattr(scan_mod.requests, "get", lambda url, **kw: _Resp(200, robots_txt))
    robots = scan_mod.load_robots("https://example.com/")

    async def never(*args, **kwargs):
        raise AssertionError("disallowed page must not be fetched")

    monkeypatch.setattr(scan_mod, "generate_report", never)
    done, results = _crawl({"max_pages": 100, "max_depth": 5, "crawl_delay": 0}, robots=robots)
    assert done == {"https://example.com/"}
    assert results == []


def test_missing_or_unreadable_robots_allows_everything(monkeypatch):
    monkeypatch.setattr(scan_mod.requests, "get", lambda url, **kw: _Resp(404))
    assert scan_mod.load_robots("https://example.com/") is None

    def boom(url, **kw):
        raise ConnectionError("down")

    monkeypatch.setattr(scan_mod.requests, "get", boom)
    assert scan_mod.load_robots("https://example.com/") is None


def test_robots_redirects_are_not_followed(monkeypatch):
    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs.get("allow_redirects")))
        return _Resp(302)

    monkeypatch.setattr(scan_mod.requests, "get", fake_get)
    assert scan_mod.load_robots("https://example.com/") is None
    assert calls == [("https://example.com/robots.txt", False)]


# --- settings ---------------------------------------------------------------------


def test_crawl_limits_come_from_settings(app):
    from models.settings import Settings

    limits = scan_mod.crawl_limits()
    assert limits == {"max_pages": 500, "max_depth": 5, "crawl_delay": 0.25}

    Settings.set("max_pages", "20")
    Settings.set("max_depth", "abc")  # invalid -> default
    Settings.set("crawl_delay_ms", "0")
    assert scan_mod.crawl_limits() == {"max_pages": 20, "max_depth": 5, "crawl_delay": 0}


# --- race-safe site creation --------------------------------------------------------


def test_get_or_create_site_reuses_a_row_created_concurrently(app, make_user, make_website, monkeypatch):
    import models.website as website_models
    from models import db

    monkeypatch.setattr(website_models, "is_valid_url", lambda url: True)
    website = make_website(make_user())
    url = website.url + "/page"

    # Simulate another worker committing the row between our lookup and our insert.
    real_init = website_models.Site.__init__

    def racing_init(self, url, website=None):
        with db.engine.begin() as other_worker:
            other_worker.execute(
                website_models.Site.__table__.insert().values(url=url, active=True, scanning=False)
            )
        real_init(self, url, website)

    monkeypatch.setattr(website_models.Site, "__init__", racing_init)

    site = scan_mod._get_or_create_site(url, website.id)
    db.session.commit()

    assert site.url == url
    assert db.session.query(website_models.Site).filter_by(url=url).count() == 1
    assert site in website.sites.all()

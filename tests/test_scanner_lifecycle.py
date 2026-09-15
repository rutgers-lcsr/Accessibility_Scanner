"""Scanner lifecycle: browser contexts are closed on every path, page results are
always well-formed, axe-core is loaded from the bundled file, and the tab-order
probe is bounded. Playwright objects are replaced with small fakes."""
import asyncio

import scanner.browser.report as report_mod
import scanner.browser.tabbable as tabbable
from scanner.accessibility import ace


def _run(coro):
    return asyncio.run(coro)


# --- fakes -----------------------------------------------------------------------


class FakeResponse:
    def __init__(self, status):
        self.status = status


class FakePage:
    def __init__(self, goto=None, url=None):
        self._goto = goto
        self.url = url

    async def goto(self, url, wait_until=None):
        self.url = self.url or url
        if isinstance(self._goto, Exception):
            raise self._goto
        return self._goto


class FakeContext:
    def __init__(self, page):
        self.page = page
        self.routes = []
        self.exited = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        self.exited = True
        return False

    async def route(self, pattern, handler):
        self.routes.append(pattern)

    async def new_page(self):
        return self.page


class FakeBrowser:
    def __init__(self, page):
        self.context = FakeContext(page)

    async def new_context(self, **kwargs):
        return self.context


# --- generate_report --------------------------------------------------------------


def test_navigation_error_gives_well_formed_report_and_closes_context():
    browser = FakeBrowser(FakePage(goto=RuntimeError("net::ERR_CONNECTION_REFUSED")))
    result = _run(report_mod.generate_report(browser, website="https://example.com/x"))

    assert result["url"] == "https://example.com/x"
    assert result["timestamp"]
    assert "ERR_CONNECTION_REFUSED" in result["error"]
    assert browser.context.exited
    assert browser.context.routes == ["**/*"]  # the non-public-host guard is installed


def test_http_error_records_status_and_closes_context():
    browser = FakeBrowser(FakePage(goto=FakeResponse(503)))
    result = _run(report_mod.generate_report(browser, website="https://example.com/"))

    assert result["response_code"] == 503
    assert "503" in result["error"]
    assert browser.context.exited


def test_offsite_redirect_is_reported_as_error():
    page = FakePage(goto=FakeResponse(200), url="https://evil.example/landing")
    browser = FakeBrowser(page)
    result = _run(report_mod.generate_report(browser, website="https://example.com/"))

    assert "Redirected off-site" in result["error"]
    assert browser.context.exited


def test_www_prefix_counts_as_same_host():
    assert report_mod._same_host("https://www.example.com/a", "https://example.com/")
    assert report_mod._same_host("http://example.com/", "https://WWW.example.com/b")
    assert not report_mod._same_host("https://other.example.com/", "https://example.com/")


def test_summary_keeps_only_small_fields():
    report = {
        "url": "https://example.com/",
        "response_code": 200,
        "base_url": "https://example.com",
        "photo": b"x" * 1024,
        "report": {"violations": [1, 2, 3]},
    }
    summary = report_mod.AccessibilitySummary.from_report(report)
    assert summary == report_mod.AccessibilitySummary(
        url="https://example.com/", response_code=200, error="", base_url="https://example.com"
    )
    assert not hasattr(summary, "photo")


# --- axe-core loading -------------------------------------------------------------


class FakeAxePage:
    def __init__(self):
        self.scripts = []
        self.evaluated = []

    async def add_script_tag(self, **kwargs):
        self.scripts.append(kwargs)

    async def wait_for_function(self, expression):
        pass

    async def evaluate(self, js):
        self.evaluated.append(js)
        return {"violations": [], "passes": [], "incomplete": [], "inapplicable": []}


def test_axe_is_loaded_from_the_bundled_file():
    page = FakeAxePage()
    result = _run(ace.get_accessibility_report(page, tags=["wcag2a"]))

    assert page.scripts == [{"path": str(ace.AXE_PATH)}]
    assert ace.AXE_PATH.exists()
    assert "axe v4.10.3" in ace.AXE_PATH.read_text(errors="ignore")[:100]
    assert result["violations"] == []
    assert "'wcag2a'" in page.evaluated[-1]


# --- tab-order probe --------------------------------------------------------------


class FakeKeyboardPage:
    """Focus walks through ``stops`` (cycling) on each Tab press."""

    def __init__(self, stops):
        self.stops = stops
        self.index = -1
        self.presses = 0
        self.keyboard = self

    async def press(self, key):
        self.presses += 1
        self.index = (self.index + 1) % len(self.stops)

    async def evaluate(self, js):
        return self.stops[self.index]


def test_page_where_focus_never_moves_is_not_tabbable():
    page = FakeKeyboardPage([{"tag": "BODY"}])
    assert _run(tabbable.is_page_tabbable(page)) is False


def test_page_with_a_focus_cycle_is_tabbable():
    page = FakeKeyboardPage([{"tag": "A", "href": "/1"}, {"tag": "A", "href": "/2"}, {"tag": "BUTTON"}])
    assert _run(tabbable.is_page_tabbable(page)) is True
    assert page.presses == 4  # first press plus three to come back around


def test_tab_probe_is_bounded(monkeypatch):
    monkeypatch.setattr(tabbable, "MAX_TAB_PRESSES", 25)
    page = FakeKeyboardPage([{"tag": "A", "href": f"/{i}"} for i in range(1000)])
    assert _run(tabbable.is_page_tabbable(page)) is True
    assert page.presses == 26

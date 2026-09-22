"""Document inventory: link detection, collection during the crawl, syncing, the PDF
checks (tagged, title, language, pages), fetch bounds, the per-scan cap and robots,
a full fake scan, the listing endpoint, and the counts."""
import asyncio
import io
import types
from datetime import datetime, timedelta, timezone
from urllib import robotparser

import pytest

import models.website as website_models
import scanner.scan as scan_mod
import services.documents as docs_mod
from models.document import Document
from scanner.browser.parse import document_type
from scanner.utils.queue import ListQueue
from services.documents import check_website_documents, fetch_pdf, inspect_pdf, sync_documents


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setattr(website_models, "is_valid_url", lambda url: True)


def _pdf(tagged=False, lang=None, title=None):
    from pypdf import PdfWriter
    from pypdf.generic import BooleanObject, DictionaryObject, NameObject, TextStringObject

    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    if tagged:
        writer._root_object[NameObject("/MarkInfo")] = DictionaryObject({NameObject("/Marked"): BooleanObject(True)})
    if lang:
        writer._root_object[NameObject("/Lang")] = TextStringObject(lang)
    if title:
        writer.add_metadata({"/Title": title})
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


# --- detection and collection -------------------------------------------------------------


def test_document_type_matches_known_extensions_only():
    assert document_type("https://x.edu/a/Syllabus.PDF") == "pdf"
    assert document_type("https://x.edu/a.docx?x=1") == "docx"
    assert document_type("https://x.edu/a.pptx#slide") == "pptx"
    assert document_type("https://x.edu/a.png") is None
    assert document_type("https://x.edu/download") is None
    assert document_type("https://x.edu/pdf/") is None


def test_crawler_collects_documents_without_queueing_them(monkeypatch):
    async def fake(browser, website, tags, ace_config):
        return {"url": website, "timestamp": "2026-01-01T00:00:00Z", "report": {"violations": []},
                "links": [], "documents": ["https://example.com/a.pdf", "https://example.com/x.png", "https://other.org/b.docx"]}

    monkeypatch.setattr(scan_mod, "generate_report", fake)
    documents = {}

    async def run():
        queue = ListQueue()
        await queue.put("https://example.com/")
        done, processing, results = set(), set(), []
        worker = asyncio.create_task(scan_mod.process_website(
            name=0, ace_config="", tags=[], browser=None, queue=queue, results=results, sites_done=done,
            currently_processing=processing, limits={"max_pages": 10, "max_depth": 5, "crawl_delay": 0},
            depths={"https://example.com/": 0}, documents=documents,
        ))
        await queue.join()
        await queue.put(None)
        await worker
        return done

    done = asyncio.run(run())
    assert done == {"https://example.com/"}
    assert documents == {
        "https://example.com/a.pdf": {"type": "pdf", "pages": {"https://example.com/"}},
        "https://other.org/b.docx": {"type": "docx", "pages": {"https://example.com/"}},
    }


# --- syncing ----------------------------------------------------------------------------------


def test_sync_creates_updates_and_removes_documents(app, make_user, make_website, add_site):
    from models import db

    website = make_website(make_user())
    home = add_site(website, page="/")
    about = add_site(website, page="/about")
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    first = sync_documents(website.id, {
        "https://example.com/a.pdf": {"type": "pdf", "pages": {home.url, about.url}},
        "https://example.com/old.docx": {"type": "docx", "pages": {home.url}},
    }, now=now - timedelta(days=7))
    assert first == {"new": 2, "updated": 0, "removed": 0}
    pdf = db.session.query(Document).filter_by(url="https://example.com/a.pdf").one()
    assert pdf.status == "pending" and pdf.to_dict()["found_on"] == sorted([home.url, about.url])
    assert db.session.query(Document).filter_by(url="https://example.com/old.docx").one().status == "not_checked"

    pdf.status = "tagged"
    db.session.commit()
    second = sync_documents(website.id, {
        "https://example.com/a.pdf": {"type": "pdf", "pages": {home.url}},
        "https://example.com/new.pdf": {"type": "pdf", "pages": {about.url}},
    }, now=now)
    assert second == {"new": 1, "updated": 1, "removed": 1}
    pdf = db.session.query(Document).filter_by(url="https://example.com/a.pdf").one()
    assert pdf.status == "tagged" and pdf.first_seen == now - timedelta(days=7) and pdf.last_seen == now
    assert pdf.to_dict()["found_on"] == [home.url]
    assert db.session.query(Document).filter_by(url="https://example.com/old.docx").first() is None
    assert website.get_document_counts() == {"total": 2, "pdf": 2, "untagged_pdf": 0, "unchecked": 1}


# --- PDF checks -------------------------------------------------------------------------------


def test_inspect_pdf_reads_tagging_title_language_and_pages():
    tagged = inspect_pdf(_pdf(tagged=True, lang="en-US", title="Syllabus"))
    assert tagged == {"status": "tagged", "title": "Syllabus", "has_title": True, "language": "en-US", "page_count": 1, "error": None}
    untagged = inspect_pdf(_pdf())
    assert untagged["status"] == "untagged" and untagged["has_title"] is False and untagged["language"] is None
    garbage = inspect_pdf(b"not a pdf at all")
    assert garbage["status"] == "unreadable" and garbage["error"]


class _Resp:
    def __init__(self, status=200, headers=None, body=b"", location=None):
        self.status_code = status
        self.headers = dict(headers or {})
        if location:
            self.headers["Location"] = location
        self.is_redirect = status in (301, 302, 303, 307, 308) and location is not None
        self.is_permanent_redirect = status in (301, 308) and location is not None
        self._body = body

    def iter_content(self, chunk_size):
        for start in range(0, len(self._body), chunk_size):
            yield self._body[start:start + chunk_size]

    def close(self):
        pass


def test_fetch_pdf_enforces_size_cap_redirect_guard_and_errors(monkeypatch):
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        if url.endswith("/big.pdf"):
            return _Resp(200, {"Content-Length": "999999999"})
        if url.endswith("/stream.pdf"):
            return _Resp(200, {}, body=b"x" * 5000)
        if url.endswith("/moved.pdf"):
            return _Resp(302, location="https://10.0.0.1/secret.pdf")
        if url.endswith("/missing.pdf"):
            return _Resp(404)
        return _Resp(200, {"Content-Length": "4"}, body=b"%PDF")

    monkeypatch.setattr(docs_mod.requests, "get", fake_get)
    monkeypatch.setattr(docs_mod, "is_safe_target", lambda url: not url.startswith("https://10."))

    assert fetch_pdf("https://example.com/ok.pdf", 1000) == (b"%PDF", "fetched", None, 4)
    assert fetch_pdf("https://example.com/big.pdf", 1000)[1] == "too_large"
    assert fetch_pdf("https://example.com/stream.pdf", 1000)[1] == "too_large"
    data, status, error, _ = fetch_pdf("https://example.com/moved.pdf", 1000)
    assert data is None and status == "unreachable" and "non-public" in error
    assert "https://10.0.0.1/secret.pdf" not in calls
    assert fetch_pdf("https://example.com/missing.pdf", 1000)[1:3] == ("unreachable", "HTTP 404")


def test_check_respects_cap_robots_recheck_window_and_host(app, make_user, make_website, add_site, monkeypatch):
    from models import db
    from models.settings import Settings

    website = make_website(make_user())
    home = add_site(website, page="/")
    sync_documents(website.id, {
        "https://example.com/a.pdf": {"type": "pdf", "pages": {home.url}},
        "https://example.com/b.pdf": {"type": "pdf", "pages": {home.url}},
        "https://example.com/private/c.pdf": {"type": "pdf", "pages": {home.url}},
        "https://elsewhere.org/d.pdf": {"type": "pdf", "pages": {home.url}},
    })
    Settings.set("document_checks_per_scan", "4")  # skipped and other-host documents do not count
    fetched = []

    def fake_fetch(url, max_bytes):
        fetched.append(url)
        return _pdf(tagged=url.endswith("a.pdf"), title="T"), "fetched", None, 1234

    monkeypatch.setattr(docs_mod, "fetch_pdf", fake_fetch)
    robots = robotparser.RobotFileParser()
    robots.parse(["User-agent: *", "Disallow: /private/"])

    assert check_website_documents(website.id, robots=robots) == 2
    by_url = {doc.url: doc for doc in db.session.query(Document).all()}
    assert by_url["https://example.com/a.pdf"].status == "tagged" and by_url["https://example.com/a.pdf"].size_bytes == 1234
    assert by_url["https://example.com/b.pdf"].status == "untagged"
    assert by_url["https://example.com/private/c.pdf"].status == "skipped"
    assert by_url["https://elsewhere.org/d.pdf"].status == "not_checked"
    assert fetched == ["https://example.com/a.pdf", "https://example.com/b.pdf"]

    # a second run within the recheck window checks nothing
    assert check_website_documents(website.id) == 0
    for doc in (by_url["https://example.com/a.pdf"], by_url["https://example.com/b.pdf"]):
        doc.checked_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=40)
    db.session.commit()
    assert check_website_documents(website.id) == 2
    assert website.get_document_counts() == {"total": 4, "pdf": 4, "untagged_pdf": 1, "unchecked": 0}


# --- the whole scan ----------------------------------------------------------------------------


class _FakePlaywright:
    async def __aenter__(self):
        async def launch(**kwargs):
            return types.SimpleNamespace(close=self._close)

        return types.SimpleNamespace(chromium=types.SimpleNamespace(launch=launch))

    async def __aexit__(self, *exc):
        return False

    async def _close(self):
        pass


def test_full_scan_records_documents(app, make_user, make_website, monkeypatch):
    from models import db

    pages = {
        "https://example.com/": {"links": ["https://example.com/about"], "documents": ["https://example.com/handbook.pdf"]},
        "https://example.com/about": {"links": [], "documents": ["https://example.com/handbook.pdf", "https://example.com/form.docx"]},
    }

    async def fake(browser, website, tags, ace_config):
        return {"url": website, "base_url": "https://example.com", "timestamp": datetime.now(timezone.utc).isoformat(),
                "report": {"violations": [], "incomplete": [], "passes": []}, "links": pages[website]["links"],
                "documents": pages[website]["documents"], "videos": [], "imgs": [], "tabable": True, "photo": None, "tags": ["wcag2a"]}

    website = make_website(make_user())
    monkeypatch.setattr(scan_mod, "check_url", lambda url: True)
    monkeypatch.setattr(scan_mod, "load_robots", lambda url: None)
    monkeypatch.setattr(scan_mod, "async_playwright", _FakePlaywright)
    monkeypatch.setattr(scan_mod, "generate_report", fake)
    monkeypatch.setattr(docs_mod, "fetch_pdf", lambda url, max_bytes: (_pdf(), "fetched", None, 10))

    asyncio.run(scan_mod.generate_reports(website.url, task_id="t-1"))

    db.session.expire_all()
    docs = {doc.url: doc for doc in db.session.query(Document).filter_by(website_id=website.id).all()}
    assert set(docs) == {"https://example.com/handbook.pdf", "https://example.com/form.docx"}
    assert docs["https://example.com/handbook.pdf"].status == "untagged"
    assert docs["https://example.com/handbook.pdf"].to_dict()["found_on"] == ["https://example.com/", "https://example.com/about"]
    assert docs["https://example.com/form.docx"].status == "not_checked"


# --- API and counts ---------------------------------------------------------------------------


def test_documents_endpoint_visibility_order_and_filters(client, make_user, make_website, add_site, jwt_header):
    from models import db

    owner = make_user("alice")
    website = make_website(owner)
    home = add_site(website, page="/")
    sync_documents(website.id, {
        "https://example.com/z.pdf": {"type": "pdf", "pages": {home.url}},
        "https://example.com/a.pdf": {"type": "pdf", "pages": {home.url}},
        "https://example.com/b.docx": {"type": "docx", "pages": {home.url}},
    })
    db.session.query(Document).filter_by(url="https://example.com/z.pdf").one().status = "untagged"
    db.session.query(Document).filter_by(url="https://example.com/a.pdf").one().status = "tagged"
    db.session.commit()

    url = f"/api/websites/{website.id}/documents/"
    assert client.get(url).status_code == 403
    assert client.get(url, headers=jwt_header(make_user("carol"))).status_code == 403
    body = client.get(url, headers=jwt_header(owner)).get_json()
    assert body["count"] == 3
    assert [d["url"] for d in body["items"]] == ["https://example.com/z.pdf", "https://example.com/a.pdf", "https://example.com/b.docx"]
    assert body["items"][0]["found_on"] == [home.url] and body["items"][0]["type"] == "pdf"
    assert client.get(url + "?status=untagged", headers=jwt_header(owner)).get_json()["count"] == 1
    assert client.get(url + "?type=docx", headers=jwt_header(owner)).get_json()["count"] == 1
    assert client.get(url + "?status=nope", headers=jwt_header(owner)).status_code == 400
    website.public = True
    assert client.get(url).status_code == 200


def test_website_dict_and_dashboard_expose_document_counts(client, make_user, make_website, add_site, jwt_header):
    from models import db

    admin = make_user("root", is_admin=True)
    website = make_website(admin)
    home = add_site(website, page="/")
    sync_documents(website.id, {
        "https://example.com/a.pdf": {"type": "pdf", "pages": {home.url}},
        "https://example.com/b.pdf": {"type": "pdf", "pages": {home.url}},
        "https://example.com/c.docx": {"type": "docx", "pages": {home.url}},
    })
    db.session.query(Document).filter_by(url="https://example.com/a.pdf").one().status = "untagged"
    db.session.commit()

    site = client.get(f"/api/websites/{website.id}/", headers=jwt_header(admin)).get_json()
    assert site["documents"] == {"total": 3, "pdf": 2, "untagged_pdf": 1, "unchecked": 1}
    dashboard = client.get("/api/dashboard/", headers=jwt_header(admin)).get_json()
    assert dashboard["totals"]["documents"] == 3 and dashboard["totals"]["untagged_pdfs"] == 1
    assert dashboard["websites"][0]["documents"] == 3 and dashboard["websites"][0]["untagged_pdfs"] == 1

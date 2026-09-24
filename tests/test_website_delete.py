"""Deleting a website removes its own pages with their reports and findings, its
documents, members, opt-outs and views, in bulk; a page shared with another website
keeps everything and only loses the link."""
import time

import pytest

import models.website as website_models
from models import db
from models.document import Document, DocumentSiteAssoc
from models.finding import Finding
from models.notifications import NotificationOptOut, WebsiteView
from models.report import Report
from models.website import Site, Site_Website_Assoc, Website
from services.findings import sync_report_findings


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setattr(website_models, "is_valid_url", lambda url: True)


def _scan(add_report, site):
    report = add_report(site)
    sync_report_findings(site.id, report.id, report.timestamp, report.report["violations"])
    db.session.commit()
    return report


def test_delete_removes_everything_of_its_own_and_unlinks_shared_pages(client, make_user, make_website, add_site, add_report, jwt_header):
    admin = make_user("root", is_admin=True)
    owner = make_user("alice")
    member = make_user("bob")
    website = make_website(owner, base="https://gone.example.com")
    other = make_website(owner, base="https://stays.example.com")
    website.users.append(member)
    own = add_site(website, page="/own")
    shared = add_site(website, page="/shared")
    shared.websites.append(other)
    theirs = add_site(other, page="/theirs")
    db.session.commit()
    for site in (own, shared, theirs):
        _scan(add_report, site)
    document = Document(website_id=website.id, url="https://gone.example.com/a.pdf", doc_type="pdf", status="pending",
                        first_seen=db.func.current_timestamp(), last_seen=db.func.current_timestamp())
    document.sites.append(own)
    db.session.add(document)
    db.session.commit()
    WebsiteView.touch(owner.id, website.id)
    website.set_subscribed(member, False)
    other.set_subscribed(owner, False)
    ids = {"website": website.id, "own": own.id, "shared": shared.id, "theirs": theirs.id, "other": other.id}

    resp = client.delete(f"/api/websites/{ids['website']}/", headers=jwt_header(admin))

    assert resp.status_code == 200
    db.session.expire_all()
    assert db.session.get(Website, ids["website"]) is None
    assert db.session.get(Site, ids["own"]) is None
    assert db.session.query(Report).filter_by(site_id=ids["own"]).count() == 0
    assert db.session.query(Finding).filter_by(site_id=ids["own"]).count() == 0
    assert db.session.query(Document).count() == 0
    assert db.session.query(DocumentSiteAssoc).count() == 0
    assert db.session.query(WebsiteView).count() == 0
    assert db.session.query(NotificationOptOut).filter_by(website_id=ids["website"]).count() == 0
    assert db.session.query(Site_Website_Assoc).filter_by(website_id=ids["website"]).count() == 0
    # the shared page and the other website are untouched
    kept = db.session.get(Site, ids["shared"])
    assert kept is not None and kept.reports.count() == 1 and kept.findings.count() == 1
    assert [w.id for w in kept.websites.all()] == [ids["other"]]
    assert db.session.get(Site, ids["theirs"]).reports.count() == 1
    assert db.session.query(NotificationOptOut).filter_by(website_id=ids["other"]).count() == 1
    assert db.session.get(Website, ids["other"]).users == []  # bob was only a member of the deleted one


def test_delete_is_a_handful_of_statements_however_many_pages(app, make_user, make_website, add_site, add_report):
    from sqlalchemy import event

    website = make_website(make_user(), base="https://big.example.com")
    for n in range(60):
        site = add_site(website, page=f"/page-{n}")
        for _ in range(2):
            _scan(add_report, site)
    statements = []
    event.listen(db.engine, "before_cursor_execute", lambda conn, cursor, statement, *a: statements.append(statement))
    started = time.perf_counter()

    website.delete()

    elapsed = time.perf_counter() - started
    assert db.session.query(Site).count() == 0 and db.session.query(Report).count() == 0
    assert len(statements) < 40, len(statements)  # not one per report or finding
    assert elapsed < 5

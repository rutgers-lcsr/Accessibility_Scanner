"""Regression tests for the backend bug batch: unsubscribe, mail in TESTING, website
creation errors, rule import, report listing order and photo, visibility filters,
website/domain deletion, and settings validation."""
import csv
import io
from datetime import datetime, timedelta, timezone

import pytest

import blueprints.website as website_bp
import models.website as website_models
from models import db


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    # Domain/Website validation resolves hostnames; keep these tests offline.
    monkeypatch.setattr(website_models, "is_valid_url", lambda url: True)
    monkeypatch.setattr(website_bp, "is_valid_url", lambda url: True)


# --- unsubscribe -------------------------------------------------------------------


def test_unsubscribe_link_round_trip(client, make_user, make_website):
    from models import db
    from utils.jwt import generate_jwt_token

    owner = make_user()
    website = make_website(owner)
    website.should_email = True
    db.session.commit()

    token = generate_jwt_token({"action": "unsubscribe", "website_id": website.id, "user_id": owner.id})
    resp = client.get(f"/api/users/unsubscribe/?token={token}")
    assert resp.status_code == 200
    assert "Stop emails about" in resp.get_data(as_text=True)
    assert website.is_subscribed(owner) is True  # a GET (a mail scanner) changes nothing

    resp = client.post("/api/users/unsubscribe/", data={"token": token})
    assert resp.status_code == 200
    assert "no longer receive" in resp.get_data(as_text=True)
    assert website.is_subscribed(owner) is False
    assert website.should_email is True  # only this user, never the whole website
    assert owner.email not in website.get_user_emails()


def test_unsubscribe_rejects_other_tokens(client, make_user, make_website):
    from utils.jwt import generate_jwt_token

    owner = make_user()
    website = make_website(owner)
    assert client.get("/api/users/unsubscribe/?token=garbage").status_code == 401
    other = generate_jwt_token({"report_id": 1, "scope": "report-script"})
    assert client.get(f"/api/users/unsubscribe/?token={other}").status_code == 401
    assert client.get("/api/users/unsubscribe/").status_code == 400
    # links from before opt-outs were per user used to silence the whole website
    legacy = generate_jwt_token({"action": "subscribe", "website_id": website.id})
    resp = client.get(f"/api/users/unsubscribe/?token={legacy}")
    assert resp.status_code == 400 and "out of date" in resp.get_json()["error"]
    assert website.should_email is True  # untouched by the rejected requests
    assert website.is_subscribed(owner) is True


def test_new_website_email_links_to_the_api_unsubscribe_endpoint(app, make_user, make_website):
    import mail.emails as emails

    website = make_website(make_user())
    website.users.append(website.admin)
    sender = emails.NewWebsiteEmail(website)
    sender.send()  # TESTING: builds the message without sending it
    assert "/api/users/unsubscribe/?token=" in sender.msg.html
    assert f'href="{website.url}"' in sender.msg.html


# --- mail under TESTING -------------------------------------------------------------


def test_mail_is_not_sent_under_testing(app, make_user, make_website, monkeypatch):
    import mail.emails as emails

    def boom(msg):
        raise AssertionError("mail must not be sent under TESTING")

    monkeypatch.setattr(emails.mail, "send", boom)
    website = make_website(make_user())
    emails.AdminNewWebsiteEmail(website).send()  # would raise before the fix


# --- website creation ---------------------------------------------------------------


def _allow_domain(name="example.com"):
    from models import db
    from models.website import Domain

    domain = Domain(domain=name)
    db.session.add(domain)
    db.session.commit()


def test_create_website_reports_validation_errors_as_400(client, make_user, make_website, jwt_header, monkeypatch):
    user = make_user()
    _allow_domain()
    make_website(user, base="https://example.com")  # already exists
    monkeypatch.setattr(website_bp, "check_url", lambda url: True)

    resp = client.post("/api/websites/", json={"base_url": "https://example.com"}, headers=jwt_header(user))
    assert resp.status_code == 400
    assert "already exists" in resp.get_json()["error"]


def test_create_website_survives_a_mail_failure(client, make_user, jwt_header, monkeypatch):
    import mail.emails as emails
    from models import db
    from models.website import Website

    user = make_user()
    _allow_domain()
    monkeypatch.setattr(website_bp, "check_url", lambda url: True)
    real_get = website_bp.Settings.get
    monkeypatch.setattr(
        website_bp.Settings,
        "get",
        lambda key, default=None: "false" if key == "default_should_auto_scan" else real_get(key, default),
    )

    def broken_send(self):
        raise RuntimeError("smtp down")

    monkeypatch.setattr(emails.AdminNewWebsiteEmail, "send", broken_send)

    resp = client.post(
        "/api/websites/", json={"base_url": "https://new.example.com", "should_email": True}, headers=jwt_header(user)
    )
    assert resp.status_code == 201
    assert db.session.query(Website).filter_by(url="https://new.example.com").one().admin_id == user.id


# --- rule import ----------------------------------------------------------------------


def test_rule_import_creates_rule_and_checks(client, make_user, jwt_header):
    admin = make_user("admin", is_admin=True)
    payload = {
        "name": "imported-rule",
        "selector": "img",
        "description": "Images need alt text",
        "help": "Add alt",
        "tags": ["custom"],
        "impact": "serious",
        "any": [
            {
                "name": "imported-check",
                "evaluate": "(node) => !!node.getAttribute('alt')",
                "pass_text": "has alt",
                "fail_text": "missing alt",
            }
        ],
    }
    resp = client.post("/api/axe/rules/import/", json=payload, headers=jwt_header(admin))
    assert resp.status_code == 201, resp.get_json()
    body = resp.get_json()
    assert body["name"] == "imported-rule"
    assert len(body["any"]) == 1

    checks = client.get(f"/api/axe/rules/{body['id']}/checks/", headers=jwt_header(admin)).get_json()
    assert checks["any"][0]["name"] == "imported-check"


def test_rule_import_requires_a_name(client, make_user, jwt_header):
    admin = make_user("admin", is_admin=True)
    resp = client.post("/api/axe/rules/import/", json={"selector": "img"}, headers=jwt_header(admin))
    assert resp.status_code == 400
    assert "name" in resp.get_json()["error"]


# --- reports listing ----------------------------------------------------------------


def _two_reports(make_user, make_site, add_report, public):
    site = make_site(make_user(), public=public)
    now = datetime.now(timezone.utc)
    older = add_report(site, when=now - timedelta(days=1))
    newer = add_report(site, when=now)
    return site, older, newer


def test_reports_desc_false_reverses_order(client, make_user, make_site, add_report):
    _, older, newer = _two_reports(make_user, make_site, add_report, public=True)

    ids = [r["id"] for r in client.get("/api/reports/").get_json()["items"]]
    assert ids == [newer.id, older.id]

    ids = [r["id"] for r in client.get("/api/reports/?desc=false").get_json()["items"]]
    assert ids == [older.id, newer.id]


def test_reports_listing_visibility(client, make_user, make_site, add_report, jwt_header):
    owner = make_user("bob")
    other = make_user("alice")
    admin = make_user("root", is_admin=True)
    private_site = make_site(owner, base="https://private.example")
    private = add_report(private_site)
    public_site = make_site(owner, base="https://public.example", public=True)
    public = add_report(public_site)

    def ids(headers=None):
        return {r["id"] for r in client.get("/api/reports/", headers=headers or {}).get_json()["items"]}

    assert ids() == {public.id}
    assert ids(jwt_header(other)) == {public.id}
    assert ids(jwt_header(owner)) == {public.id, private.id}
    assert ids(jwt_header(admin)) == {public.id, private.id}


def test_report_photo_404_when_missing(client, make_user, make_site, add_report, jwt_header):
    user = make_user()
    report = add_report(make_site(user))  # fixture stores photo=None
    resp = client.get(f"/api/reports/{report.id}/photo/", headers=jwt_header(user))
    assert resp.status_code == 404


# --- website listing visibility ------------------------------------------------------


def test_websites_listing_visibility(client, make_user, make_website, jwt_header):
    from models import db

    owner = make_user("bob")
    member = make_user("carol")
    other = make_user("alice")
    admin = make_user("root", is_admin=True)
    private = make_website(owner, base="https://private.example")
    shared = make_website(owner, base="https://shared.example")
    shared.users.append(member)
    public = make_website(owner, base="https://public.example", public=True)
    db.session.commit()

    def ids(headers=None):
        return {w["id"] for w in client.get("/api/websites/", headers=headers or {}).get_json()["items"]}

    assert ids() == {public.id}
    assert ids(jwt_header(other)) == {public.id}
    assert ids(jwt_header(member)) == {public.id, shared.id}
    assert ids(jwt_header(owner)) == {public.id, shared.id, private.id}
    assert ids(jwt_header(admin)) == {public.id, shared.id, private.id}


def test_categories_listing_uses_visibility(client, make_user, make_website, jwt_header):
    from models import db

    owner = make_user("bob")
    other = make_user("alice")
    private = make_website(owner, base="https://private.example")
    private.categories = "secret"
    public = make_website(owner, base="https://public.example", public=True)
    public.categories = "open, shared"
    db.session.commit()

    assert client.get("/api/websites/categories/", headers=jwt_header(other)).get_json() == ["open", "shared"]
    assert client.get("/api/websites/categories/", headers=jwt_header(owner)).get_json() == ["open", "secret", "shared"]


# --- deletion ------------------------------------------------------------------------


def test_delete_website_keeps_shared_pages_and_removes_its_domain(app, make_user, make_website, add_site):
    from models import db
    from models.website import Domain, Site, Website

    owner = make_user()
    first = make_website(owner, base="https://first.example")
    second = make_website(owner, base="https://second.example")
    own_page = add_site(first, page="/only-first")
    shared_page = add_site(first, page="/shared")
    shared_page.websites.append(second)
    db.session.commit()
    first_id, second_id, own_id, shared_id = first.id, second.id, own_page.id, shared_page.id

    first.delete()

    assert db.session.get(Website, first_id) is None
    assert db.session.get(Website, second_id) is not None
    assert db.session.get(Site, own_id) is None
    assert db.session.get(Site, shared_id) is not None
    assert db.session.query(Domain).filter_by(domain="first.example").first() is None
    assert db.session.query(Domain).filter_by(domain="second.example").first() is not None


def test_delete_domain_deletes_its_websites_once(app, make_user, make_website, add_site):
    from models import db
    from models.website import Domain, Site, Website

    website = make_website(make_user(), base="https://gone.example")
    page = add_site(website, page="/p")
    domain = db.session.query(Domain).filter_by(domain="gone.example").one()
    website_id, page_id, domain_id = website.id, page.id, domain.id

    domain.delete()

    assert db.session.get(Domain, domain_id) is None
    assert db.session.get(Website, website_id) is None
    assert db.session.get(Site, page_id) is None


# --- settings validation --------------------------------------------------------------


def test_settings_reject_invalid_values(client, make_user, jwt_header):
    from models.settings import Settings

    admin = make_user("root", is_admin=True)
    headers = jwt_header(admin)
    before = Settings.get("default_rate_limit")

    resp = client.put("/api/settings/", json={"default_rate_limit": "abc"}, headers=headers)
    assert resp.status_code == 400
    assert "default_rate_limit" in resp.get_json()["error"]
    assert Settings.get("default_rate_limit") == before

    assert client.put("/api/settings/", json={"default_should_auto_scan": "maybe"}, headers=headers).status_code == 400
    assert client.put("/api/settings/", json={"default_email_domain": "not a host"}, headers=headers).status_code == 400
    assert client.put("/api/settings/", json={"max_depth": -1}, headers=headers).status_code == 400
    assert client.put("/api/settings/", json={"unknown_key": 1}, headers=headers).status_code == 400


def test_settings_accept_and_normalise_valid_values(client, make_user, jwt_header):
    from models.settings import Settings

    admin = make_user("root", is_admin=True)
    resp = client.put(
        "/api/settings/",
        json={
            "default_rate_limit": 14,
            "default_should_auto_scan": "TRUE",
            "default_email_domain": "Rutgers.EDU",
            "default_tags": " wcag2a ,wcag21aa,, ",
            "max_depth": 0,
        },
        headers=jwt_header(admin),
    )
    assert resp.status_code == 200, resp.get_json()
    assert Settings.get("default_rate_limit") == "14"
    assert Settings.get("default_should_auto_scan") == "true"
    assert Settings.get("default_email_domain") == "rutgers.edu"
    assert Settings.get("default_tags") == "wcag2a, wcag21aa"
    assert Settings.get("max_depth") == "0"


def test_num_of_links_counts_the_list(app, make_user, make_site, add_report):
    report = add_report(make_site(make_user()))
    report.links = ["a", "b"]
    assert report.num_of_links == 2


# --- settings defaults ----------------------------------------------------------------


def test_settings_get_falls_back_to_the_declared_default(app):
    from models import db
    from models.settings import DEFAULTS, Settings

    db.session.query(Settings).filter_by(key="max_pages").delete()
    db.session.commit()
    assert Settings.get("max_pages") == DEFAULTS["max_pages"] == "500"
    assert Settings.get("max_pages", "7") == "7"


def test_new_website_defaults_follow_the_declared_defaults(app, make_user):
    """The call sites used to carry their own defaults, opposite to init_defaults."""
    from models import db
    from models.settings import Settings
    from models.website import Domain, Website

    for key in ("default_should_auto_activate", "default_notify_on_completion", "default_rate_limit"):
        db.session.query(Settings).filter_by(key=key).delete()
    db.session.commit()
    domain = Domain(domain="example.com")
    db.session.add(domain)
    db.session.commit()

    website = Website(url="https://example.com", user_id=make_user().id)

    assert website.active is False
    assert website.should_email is True
    assert website.rate_limit == 30


# --- csv export -----------------------------------------------------------------------


def test_websites_csv_export_lists_websites(client, make_user, make_website, jwt_header):
    admin = make_user("root", is_admin=True)
    make_website(admin, base="https://export.example.com")

    resp = client.get("/api/websites/?format=csv", headers=jwt_header(admin))

    assert resp.status_code == 200
    assert resp.mimetype == "text/csv"
    body = resp.get_data(as_text=True)
    assert "https://export.example.com" in body
    assert body.splitlines()[0].startswith("id,url")


def test_websites_csv_includes_and_quotes_the_description(client, make_user, make_website, jwt_header):
    admin = make_user("root", is_admin=True)
    website = make_website(admin, base="https://export.example.com")
    website.description = 'Lab, "main" site\nsecond line'
    db.session.commit()

    resp = client.get("/api/websites/?format=csv", headers=jwt_header(admin))

    rows = list(csv.reader(io.StringIO(resp.get_data(as_text=True))))
    row = dict(zip(rows[0], rows[1]))
    assert row["description"] == 'Lab, "main" site\nsecond line'
    assert row["admin"] == "root"


def test_websites_search_matches_the_admin_user(client, make_user, make_website, jwt_header):
    admin = make_user("root", is_admin=True)
    make_website(make_user("alice"), base="https://alpha.example.com")
    make_website(make_user("bob"), base="https://beta.example.com")

    def urls(search):
        resp = client.get(f"/api/websites/?search={search}", headers=jwt_header(admin))
        assert resp.status_code == 200
        return [w["url"] for w in resp.get_json()["items"]]

    assert urls("bob") == ["https://beta.example.com"]
    assert urls("alpha") == ["https://alpha.example.com"]

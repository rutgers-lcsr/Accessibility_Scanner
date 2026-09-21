"""Website creation: the parent-domain allow-list is checked before any network probe."""
import pytest

import blueprints.website as website_bp
import models.website as website_models


@pytest.fixture(autouse=True)
def _no_dns(monkeypatch):
    # Domain/Website validation resolves hostnames; keep these tests offline.
    monkeypatch.setattr(website_models, "is_valid_url", lambda url: True)
    monkeypatch.setattr(website_bp, "is_valid_url", lambda url: True)


def _domain(name, active=True):
    from models import db
    from models.website import Domain

    domain = Domain(domain=name)
    domain.active = active
    db.session.add(domain)
    db.session.commit()
    return domain


def test_find_parent_domain_matches_host_and_subdomains(app):
    from models.website import Website

    _domain("rutgers.edu")
    assert Website.find_parent_domain("https://rutgers.edu/").domain == "rutgers.edu"
    assert Website.find_parent_domain("https://cs.rutgers.edu/some/page").domain == "rutgers.edu"
    assert Website.find_parent_domain("https://CS.Rutgers.EDU/").domain == "rutgers.edu"


def test_find_parent_domain_prefers_most_specific(app):
    from models.website import Website

    _domain("rutgers.edu")
    _domain("cs.rutgers.edu")
    assert Website.find_parent_domain("https://web.cs.rutgers.edu/").domain == "cs.rutgers.edu"
    assert Website.find_parent_domain("https://math.rutgers.edu/").domain == "rutgers.edu"


def test_find_parent_domain_rejects_lookalike_hosts(app):
    from models.website import Website

    _domain("rutgers.edu")
    assert Website.find_parent_domain("https://evil-rutgers.edu/") is None
    assert Website.find_parent_domain("https://rutgers.edu.attacker.example/") is None
    assert Website.find_parent_domain("https://example.com/") is None


def test_find_parent_domain_ignores_inactive_domains(app):
    from models.website import Website

    _domain("rutgers.edu", active=False)
    assert Website.find_parent_domain("https://cs.rutgers.edu/") is None


def test_create_website_checks_allow_list_before_probing(client, make_user, jwt_header, monkeypatch):
    user = make_user()

    def never(url):
        raise AssertionError("check_url must not run for a host outside the allow-list")

    monkeypatch.setattr(website_bp, "check_url", never)
    resp = client.post(
        "/api/websites/", json={"base_url": "https://not-allowed.example/"}, headers=jwt_header(user)
    )
    assert resp.status_code == 400
    assert "parent domain" in resp.get_json()["error"]


# --- site admins: allow-list the host, choose the admin user, set categories ------------


import types


def _never(url):
    raise AssertionError("check_url must not run for a host outside the allow-list")


@pytest.fixture()
def created(monkeypatch):
    """Make the create path succeed offline: the probe passes and no scan is queued."""
    import scanner.tasks as tasks_mod

    monkeypatch.setattr(website_bp, "check_url", lambda url: True)
    monkeypatch.setattr(tasks_mod.scan_website, "delay", lambda url: types.SimpleNamespace(id="t-1"))


def test_missing_domain_error_names_the_host(client, make_user, jwt_header, monkeypatch):
    from models import db
    from models.website import Domain

    admin = make_user("root", is_admin=True)
    monkeypatch.setattr(website_bp, "check_url", _never)

    resp = client.post(
        "/api/websites/", json={"base_url": "https://cs.rutgers.edu/"}, headers=jwt_header(admin)
    )
    assert resp.status_code == 400
    body = resp.get_json()
    assert body["code"] == "no_parent_domain"
    assert body["domain"] == "cs.rutgers.edu"
    assert db.session.query(Domain).count() == 0


def test_admin_can_add_the_domain_with_the_website(client, make_user, jwt_header, created):
    from models import db
    from models.website import Domain, Website

    admin = make_user("root", is_admin=True)
    resp = client.post(
        "/api/websites/",
        json={"base_url": "https://cs.rutgers.edu/", "create_domain": True},
        headers=jwt_header(admin),
    )
    assert resp.status_code == 201
    domain = db.session.query(Domain).filter_by(domain="cs.rutgers.edu").one()
    assert domain.active
    website = db.session.get(Website, resp.get_json()["id"])
    assert website.domain_id == domain.id
    assert website.admin.username == "root"


def test_domain_is_not_kept_when_the_website_is_unreachable(client, make_user, jwt_header, monkeypatch):
    from models import db
    from models.website import Domain

    admin = make_user("root", is_admin=True)
    monkeypatch.setattr(website_bp, "check_url", lambda url: False)

    resp = client.post(
        "/api/websites/",
        json={"base_url": "https://cs.rutgers.edu/", "create_domain": True},
        headers=jwt_header(admin),
    )
    assert resp.status_code == 400
    assert db.session.query(Domain).filter_by(domain="cs.rutgers.edu").first() is None


def test_create_domain_is_ignored_for_non_admins(client, make_user, jwt_header, monkeypatch):
    from models import db
    from models.website import Domain

    user = make_user()
    monkeypatch.setattr(website_bp, "check_url", _never)

    resp = client.post(
        "/api/websites/",
        json={"base_url": "https://cs.rutgers.edu/", "create_domain": True},
        headers=jwt_header(user),
    )
    assert resp.status_code == 400
    assert resp.get_json()["code"] == "no_parent_domain"
    assert db.session.query(Domain).count() == 0


def test_an_inactive_domain_is_reactivated_instead_of_duplicated(client, make_user, jwt_header, created):
    from models import db
    from models.website import Domain

    _domain("cs.rutgers.edu", active=False)
    admin = make_user("root", is_admin=True)

    resp = client.post(
        "/api/websites/",
        json={"base_url": "https://cs.rutgers.edu/", "create_domain": True},
        headers=jwt_header(admin),
    )
    assert resp.status_code == 201
    assert db.session.query(Domain).filter_by(domain="cs.rutgers.edu").one().active
    assert db.session.query(Domain).count() == 1


def test_admin_can_set_the_admin_user_and_categories(client, make_user, jwt_header, created):
    _domain("rutgers.edu")
    admin = make_user("root", is_admin=True)
    make_user("bob")

    resp = client.post(
        "/api/websites/",
        json={"base_url": "https://cs.rutgers.edu/", "admin": "bob", "categories": ["Course", " labs ", ""]},
        headers=jwt_header(admin),
    )
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["admin"] == "bob"
    assert body["categories"] == ["Course", "labs"]


def test_unknown_admin_user_is_created_with_the_default_email_domain(client, make_user, jwt_header, created):
    from models import db
    from models.settings import Settings
    from models.user import User

    _domain("rutgers.edu")
    admin = make_user("root", is_admin=True)
    payload = {"base_url": "https://cs.rutgers.edu/", "admin": "newbie"}

    resp = client.post("/api/websites/", json=payload, headers=jwt_header(admin))
    assert resp.status_code == 400
    assert "email domain" in resp.get_json()["error"]
    assert db.session.query(User).filter_by(username="newbie").first() is None

    Settings.set("default_email_domain", "rutgers.edu")
    resp = client.post("/api/websites/", json=payload, headers=jwt_header(admin))
    assert resp.status_code == 201
    assert resp.get_json()["admin"] == "newbie"
    assert db.session.query(User).filter_by(username="newbie").one().email == "newbie@rutgers.edu"


def test_admin_fields_are_ignored_for_non_admins(client, make_user, jwt_header, created):
    _domain("rutgers.edu")
    user = make_user("alice")
    make_user("bob")

    resp = client.post(
        "/api/websites/",
        json={"base_url": "https://cs.rutgers.edu/", "admin": "bob", "categories": ["x"]},
        headers=jwt_header(user),
    )
    assert resp.status_code == 201
    assert resp.get_json()["admin"] == "alice"
    assert resp.get_json()["categories"] == []

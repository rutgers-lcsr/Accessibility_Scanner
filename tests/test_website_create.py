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

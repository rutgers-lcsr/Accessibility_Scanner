"""Site health: header, platform and requirement parsing, storing checks (uptime
history, up/down flips), scheduling, the endpoints and content requirements."""
from datetime import datetime, timedelta

import pytest
from bs4 import BeautifulSoup

import models.website as website_models
import services.health as health_mod
from models import db
from models.health import ContentRequirement, HealthCheck, WebsiteHealth
from services.health import check_requirement, fingerprint, record_health, security_headers, uptime


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setattr(website_models, "is_valid_url", lambda url: True)


def _found(up=True, status=200, headers=None, html="", requirements=None, tls=None):
    return {
        "page": {"up": up, "status_code": status if up or status else None, "response_ms": 120 if up else None,
                 "final_url": "https://example.com/", "headers": headers or {}, "html": html,
                 "error": None if up else "ConnectionError: refused"},
        "tls": tls or {"valid": True, "expires_at": datetime(2027, 1, 1), "issuer": "Let's Encrypt", "error": None},
        "https_redirect": True,
        "headers": security_headers(headers or {}) if up else {},
        "fingerprint": fingerprint(headers or {}, html) if up else None,
        "requirements": requirements,
    }


# --- parsing --------------------------------------------------------------------------------


def test_security_headers_case_insensitive_and_frame_ancestors():
    found = security_headers({"strict-transport-security": "max-age=31536000",
                              "Content-Security-Policy": "default-src 'self'; frame-ancestors 'none'"})
    assert found["Strict-Transport-Security"] == "max-age=31536000"
    assert found["X-Frame-Options"] == "CSP frame-ancestors"
    assert found["Referrer-Policy"] is None and found["X-Content-Type-Options"] is None


@pytest.mark.parametrize("headers,html,expected", [
    ({}, '<meta name="generator" content="WordPress 6.7.1">', ("WordPress", "6.7.1")),
    ({"X-Generator": "Drupal 10 (https://www.drupal.org)"}, "", ("Drupal", "10")),
    ({}, '<meta name="Generator" content="Hugo 0.128.0">', ("Hugo", "0.128.0")),
    ({}, '<link href="/wp-content/themes/x/style.css">', ("WordPress", None)),
    ({}, '<script type="application/json" data-drupal-selector="drupal-settings-json">', ("Drupal", None)),
    ({}, '<script id="__NEXT_DATA__">', ("Next.js", None)),
    ({"X-Powered-By": "PHP/8.2.1"}, "<p>hi</p>", ("PHP", None)),
    ({}, "<p>plain</p>", (None, None)),
])
def test_fingerprint(headers, html, expected):
    found = fingerprint({**headers, "Server": "nginx"}, html)
    assert (found["platform"], found["version"]) == expected
    assert found["server"] == "nginx"


@pytest.mark.parametrize("check_type,pattern,passed", [
    ("link_text", r"accessibility", True),
    ("link_text", r"privacy", False),
    ("link_href", r"rutgers\.edu/accessibility", True),
    ("selector", "footer .copyright", True),
    ("selector", "footer .missing", False),
    ("text", r"©\s*\d{4}\s*Rutgers", True),
    ("link_text", r"(", False),  # invalid regex never passes
])
def test_check_requirement(check_type, pattern, passed):
    html = ('<a href="https://www.rutgers.edu/accessibility">Accessibility statement</a>'
            '<footer><p class="copyright">© 2026 Rutgers, The State University</p></footer>')
    requirement = type("R", (), {"id": 1, "name": "x", "check_type": check_type, "pattern": pattern})()
    result = check_requirement(requirement, BeautifulSoup(html, "html.parser"))
    assert result["passed"] is passed


# --- storing ---------------------------------------------------------------------------------


def test_record_health_appends_history_and_tracks_flips(app, make_user, make_website):
    website = make_website(make_user())
    t0 = datetime(2026, 11, 1, 12, 0)
    html = '<meta name="generator" content="WordPress 6.7">'
    record_health(website, _found(headers={"X-Content-Type-Options": "nosniff"}, html=html), t0)
    db.session.commit()
    health = db.session.get(WebsiteHealth, website.id)
    assert health.up is True and health.up_changed_at == t0
    assert health.platform == "WordPress" and health.platform_version == "6.7"
    assert health.security_headers["X-Content-Type-Options"] == "nosniff"
    assert health.tls_valid is True and health.tls_issuer == "Let's Encrypt"

    record_health(website, _found(html=html), t0 + timedelta(minutes=15))
    db.session.commit()
    assert health.up_changed_at == t0  # still up: no flip

    t2 = t0 + timedelta(minutes=30)
    record_health(website, _found(up=False, status=None), t2)
    db.session.commit()
    assert health.up is False and health.up_changed_at == t2
    assert health.platform == "WordPress"  # a failed fetch keeps what it cannot know
    assert db.session.query(HealthCheck).filter_by(website_id=website.id).count() == 3


def test_uptime_percentages(app, make_user, make_website):
    website = make_website(make_user())
    now = datetime(2026, 11, 17, 12, 0)
    for hours, up in ((1, True), (2, False), (30, True), (24 * 10, False)):
        db.session.add(HealthCheck(website_id=website.id, checked_at=now - timedelta(hours=hours), up=up))
    db.session.commit()
    result = uptime(website.id, now)
    assert result["day"] == 50.0
    assert result["week"] == pytest.approx(66.67)
    assert result["month"] == 50.0
    assert result["checks"] == 4


def test_uptime_without_checks_is_none(app, make_user, make_website):
    website = make_website(make_user())
    assert uptime(website.id) == {"day": None, "week": None, "month": None, "checks": 0}


# --- scheduling -------------------------------------------------------------------------------


def test_run_checks_only_due_not_retired_and_prunes(app, make_user, make_website, monkeypatch):
    owner = make_user()
    due = make_website(owner, base="https://due.example")
    fresh = make_website(owner, base="https://fresh.example")
    retired = make_website(owner, base="https://retired.example")
    retired.lifecycle_status = "retired"
    now = datetime(2026, 11, 17, 12, 0)
    db.session.add(WebsiteHealth(website_id=fresh.id, checked_at=now - timedelta(minutes=5), up=True))
    db.session.add(HealthCheck(website_id=due.id, checked_at=now - timedelta(days=200), up=True))
    db.session.commit()
    probed = []
    monkeypatch.setattr(health_mod, "probe_website", lambda url, reqs: probed.append(url) or _found())

    result = health_mod.run_health_checks(now)

    assert probed == ["https://due.example"]
    assert result == {"checked": 1, "pruned": 1}
    assert db.session.get(WebsiteHealth, due.id).up is True


def test_run_checks_switched_off(app, monkeypatch):
    from models.settings import Settings
    Settings.set("health_checks_enabled", "false")
    monkeypatch.setattr(health_mod, "probe_website", lambda url, reqs: pytest.fail("should not probe"))
    assert health_mod.run_health_checks() == {"checked": 0, "pruned": 0}


def test_probe_passes_assigned_enabled_requirements(app, make_user, make_website, monkeypatch):
    website = make_website(make_user())
    on = ContentRequirement(name="A11y link", check_type="link_text", pattern="accessibility", enabled=True)
    off = ContentRequirement(name="Old", check_type="text", pattern="x", enabled=False)
    on.websites = [website]
    off.websites = [website]
    db.session.add_all([on, off])
    db.session.commit()
    seen = {}
    monkeypatch.setattr(health_mod, "probe_website",
                        lambda url, reqs: seen.setdefault("names", [r.name for r in reqs]) and _found(
                            requirements=[{"id": on.id, "name": on.name, "passed": True, "detail": None}]))
    health = health_mod.check_website(website)
    assert seen["names"] == ["A11y link"]
    assert health.requirements[0]["passed"] is True


# --- endpoints --------------------------------------------------------------------------------


def test_health_endpoint_permissions_and_shape(client, jwt_header, make_user, make_website):
    owner, stranger = make_user("owner"), make_user("stranger")
    website = make_website(owner)
    record_health(website, _found(headers={"Strict-Transport-Security": "max-age=1"}), datetime.utcnow())
    db.session.commit()

    assert client.get(f"/api/websites/{website.id}/health/", headers=jwt_header(stranger)).status_code == 403
    assert client.get(f"/api/websites/{website.id}/health/").status_code == 403
    body = client.get(f"/api/websites/{website.id}/health/", headers=jwt_header(owner)).get_json()
    assert body["health"]["up"] is True
    assert body["health"]["security_headers"]["Strict-Transport-Security"] == "max-age=1"
    assert "tls_days_left" in body["health"] and body["uptime"]["checks"] == 1
    assert len(body["recent"]) == 1
    assert "Content-Security-Policy" in body["security_headers"]


def test_check_now_requires_edit_rights(client, jwt_header, make_user, make_website, monkeypatch):
    owner, stranger = make_user("owner"), make_user("stranger")
    website = make_website(owner, public=True)
    monkeypatch.setattr(health_mod, "probe_website", lambda url, reqs: _found())
    assert client.post(f"/api/websites/{website.id}/health/check/", headers=jwt_header(stranger)).status_code == 403
    resp = client.post(f"/api/websites/{website.id}/health/check/", headers=jwt_header(owner))
    assert resp.status_code == 200 and resp.get_json()["health"]["up"] is True


def test_requirements_crud_and_assignment(client, jwt_header, make_user, make_website):
    admin, owner = make_user("root", is_admin=True), make_user("owner")
    website = make_website(owner)
    body = {"name": "Accessibility statement", "check_type": "link_text", "pattern": "accessibility",
            "website_ids": [website.id]}
    assert client.post("/api/requirements/", json=body, headers=jwt_header(owner)).status_code == 403
    resp = client.post("/api/requirements/", json=body, headers=jwt_header(admin))
    assert resp.status_code == 201
    requirement = resp.get_json()
    assert requirement["website_ids"] == [website.id]

    bad = client.post("/api/requirements/", json={**body, "pattern": "("}, headers=jwt_header(admin))
    assert bad.status_code == 400
    bad = client.post("/api/requirements/", json={**body, "check_type": "magic"}, headers=jwt_header(admin))
    assert bad.status_code == 400

    resp = client.patch(f"/api/requirements/{requirement['id']}/", json={"website_ids": []}, headers=jwt_header(admin))
    assert resp.get_json()["website_ids"] == []

    # Assigned from the website's side too (site admins only).
    resp = client.patch(f"/api/websites/{website.id}/", json={"requirement_ids": [requirement["id"]]},
                        headers=jwt_header(admin))
    assert resp.status_code == 200
    assert [r.id for r in db.session.get(website_models.Website, website.id).requirements] == [requirement["id"]]

    listed = client.get("/api/requirements/", headers=jwt_header(owner)).get_json()
    assert [r["name"] for r in listed] == ["Accessibility statement"]
    assert client.delete(f"/api/requirements/{requirement['id']}/", headers=jwt_header(admin)).status_code == 204
    assert db.session.query(ContentRequirement).count() == 0


def test_deleting_a_website_removes_its_health(app, make_user, make_website):
    website = make_website(make_user())
    requirement = ContentRequirement(name="x", check_type="text", pattern="x")
    requirement.websites = [website]
    db.session.add(requirement)
    record_health(website, _found(), datetime.utcnow())
    db.session.commit()
    website.delete()
    assert db.session.query(HealthCheck).count() == 0
    assert db.session.query(WebsiteHealth).count() == 0
    assert db.session.get(ContentRequirement, requirement.id).websites == []

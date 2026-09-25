"""Tests for custom axe rules through the API-key surface (/api/v1/rules)."""
import pytest

import models.website as website_models


@pytest.fixture(autouse=True)
def _no_dns(monkeypatch):
    # Domain/Website validation resolves hostnames; keep these tests offline.
    monkeypatch.setattr(website_models, "is_valid_url", lambda url: True)


def _key_header(token):
    return {"X-API-Key": token}


def _rule_body(**overrides):
    body = {
        "name": "image-alt-not-file-name",
        "description": "Ensures image alt text is not the image's file name",
        "help": "Image alt text must describe the image, not name its file",
        "impact": "serious",
        "tags": ["wcag2a", "wcag111"],
        "selector": "img[alt]",
        "none": [
            {
                "name": "alt-is-file-name",
                "evaluate": "(node) => /\\.(png|jpe?g|gif)$/i.test(node.getAttribute('alt').trim())",
                "pass_text": "Alt text is not a file name",
                "fail_text": "Alt text is a file name",
            }
        ],
    }
    body.update(overrides)
    return body


@pytest.fixture()
def admin_token(make_user, make_api_key):
    _, token = make_api_key(make_user("admin", is_admin=True))
    return token


def _post(client, token, body, query=""):
    return client.post(f"/api/v1/rules{query}", json=body, headers=_key_header(token))


def _active_website(make_website, owner, base="https://example.com", tags=None):
    from models import db

    website = make_website(owner, base=base)
    website.active = True
    website.tags = tags
    db.session.commit()
    return website


def _field_errors(resp):
    assert resp.status_code == 400
    return {e["field"]: e["message"] for e in resp.get_json()["errors"]}


def test_rules_require_a_key(client):
    assert client.get("/api/v1/rules").status_code == 401
    assert client.post("/api/v1/rules", json=_rule_body()).status_code == 401


def test_rules_require_a_site_admin(client, make_user, make_api_key):
    _, token = make_api_key(make_user())
    assert _post(client, token, _rule_body()).status_code == 403
    assert client.get("/api/v1/rules", headers=_key_header(token)).status_code == 403
    assert client.get("/api/v1/rules/1", headers=_key_header(token)).status_code == 403


def test_create_saves_rule_and_checks(client, admin_token, make_user, make_website):
    from models import db
    from models.rules import Rule

    _active_website(make_website, make_user())
    resp = _post(client, admin_token, _rule_body())
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["id"] is not None
    assert body["tags"] == ["wcag2a", "wcag111"]
    assert body["none"][0]["name"] == "alt-is-file-name"
    assert body["any"] == [] and body["all"] == []
    # wcag2a is a default tag, so every active website runs the rule
    assert body["websites_running"] == 1

    rule = db.session.get(Rule, body["id"])
    assert [check.name for check in rule.none] == ["alt-is-file-name"]
    assert rule.enabled is True


def test_saved_rule_reaches_the_scan_config(client, admin_token):
    from models.website import ace_config_for_tags

    assert _post(client, admin_token, _rule_body()).status_code == 201
    config = ace_config_for_tags(["wcag2a", "wcag2aa"])
    assert '"image-alt-not-file-name"' in config
    assert '"alt-is-file-name"' in config


def test_websites_running_counts_only_matching_tags(client, admin_token, make_user, make_website):
    owner = make_user()
    _active_website(make_website, owner, "https://a.example.com", tags="custom-dept")
    _active_website(make_website, owner, "https://b.example.com")

    resp = _post(client, admin_token, _rule_body(tags=["custom-dept"]))
    assert resp.status_code == 201
    assert resp.get_json()["websites_running"] == 1

    resp = _post(client, admin_token, _rule_body(
        name="nowhere", tags=["unused-tag"], none=[{**_rule_body()["none"][0], "name": "other-check"}],
    ))
    assert resp.status_code == 201
    assert resp.get_json()["websites_running"] == 0


def test_dry_run_saves_nothing(client, admin_token):
    from models import db
    from models.rules import Check, Rule

    resp = _post(client, admin_token, _rule_body(), "?dry_run=true")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["id"] is None
    assert body["name"] == "image-alt-not-file-name"
    assert db.session.query(Rule).count() == 0
    assert db.session.query(Check).count() == 0

    # the same body still saves afterwards
    assert _post(client, admin_token, _rule_body()).status_code == 201


def test_dry_run_still_reports_errors(client, admin_token):
    errors = _field_errors(_post(client, admin_token, _rule_body(impact="huge"), "?dry_run=true"))
    assert "impact" in errors


def test_every_problem_is_reported_at_once(client, admin_token):
    body = _rule_body(impact="huge", tags=[], extra=1)
    del body["help"]
    body["none"][0]["evaluate"] = "function (node) { return true }"
    body["none"][0]["color"] = "red"
    del body["none"][0]["fail_text"]

    errors = _field_errors(_post(client, admin_token, body))
    assert set(errors) == {
        "extra", "help", "impact", "tags", "none[0].color", "none[0].fail_text",
    }


def test_check_code_errors_name_the_check(client, admin_token):
    body = _rule_body()
    body["none"][0]["evaluate"] = "function (node) { return true }"
    errors = _field_errors(_post(client, admin_token, body))
    assert set(errors) == {"none[0]"}
    assert "evaluate" in errors["none[0]"]


def test_rule_code_errors_are_reported(client, admin_token):
    errors = _field_errors(_post(client, admin_token, _rule_body(matches="node => {")))
    assert "matches" in errors["rule"]


def test_a_rule_needs_a_check(client, admin_token):
    errors = _field_errors(_post(client, admin_token, _rule_body(none=[])))
    assert "any" in errors


def test_names_must_be_unique(client, admin_token):
    assert _post(client, admin_token, _rule_body()).status_code == 201

    errors = _field_errors(_post(client, admin_token, _rule_body()))
    assert set(errors) == {"name", "none[0].name"}

    check = _rule_body()["none"][0]
    errors = _field_errors(_post(client, admin_token, _rule_body(
        name="another",
        any=[{**check, "name": "twice"}],
        none=[{**check, "name": "twice"}],
    )))
    assert set(errors) == {"none[0].name"}


def test_non_object_body_is_rejected(client, admin_token):
    resp = client.post("/api/v1/rules", data="nope", headers=_key_header(admin_token))
    assert _field_errors(resp) == {"body": "must be a JSON object"}


def test_fetched_rule_can_be_sent_back(client, admin_token):
    created = _post(client, admin_token, _rule_body()).get_json()

    fetched = client.get(f"/api/v1/rules/{created['id']}", headers=_key_header(admin_token))
    assert fetched.status_code == 200
    body = fetched.get_json()
    assert body == created

    body["name"] = "copy"
    body["none"][0]["name"] = "copy-check"
    resp = _post(client, admin_token, body)
    assert resp.status_code == 201
    assert resp.get_json()["id"] != created["id"]


def test_get_unknown_rule_is_not_found(client, admin_token):
    assert client.get("/api/v1/rules/999", headers=_key_header(admin_token)).status_code == 404


def test_list_rules_with_search(client, admin_token):
    _post(client, admin_token, _rule_body())
    check = _rule_body()["none"][0]
    _post(client, admin_token, _rule_body(name="link-text", none=[{**check, "name": "c2"}]))

    resp = client.get("/api/v1/rules", headers=_key_header(admin_token))
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["count"] == 2
    assert [rule["name"] for rule in body["items"]] == ["image-alt-not-file-name", "link-text"]

    resp = client.get("/api/v1/rules?search=LINK", headers=_key_header(admin_token))
    assert [rule["name"] for rule in resp.get_json()["items"]] == ["link-text"]


def test_rules_are_in_the_api_docs(client):
    spec = client.get("/api/apispec_1.json").get_json()
    assert {"get", "post"} <= set(spec["paths"]["/api/v1/rules"])
    assert "RuleCheck" in spec["definitions"]


def test_builtin_axe_names_are_rejected(client, admin_token):
    check = {**_rule_body()["none"][0], "name": "has-alt"}
    errors = _field_errors(_post(client, admin_token, _rule_body(name="image-alt", none=[check])))
    assert "built-in axe-core check" in errors["none[0]"]
    assert "built-in axe-core rule" in errors["rule"]

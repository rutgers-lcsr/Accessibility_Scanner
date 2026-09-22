"""Report storage: passes and inapplicable rules are stored without their node lists,
the phantom 'inaccessible' bucket is gone, and the screenshot is loaded only by the
photo endpoint, which serves the PNG bytes with cache headers."""
import pytest
from sqlalchemy import inspect

import models.website as website_models
from scanner.accessibility.ace import slim_axe_report


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setattr(website_models, "is_valid_url", lambda url: True)


def _rule(rule_id, nodes=2, impact="serious"):
    return {
        "id": rule_id,
        "impact": impact,
        "description": f"{rule_id} description",
        "help": f"Fix {rule_id}",
        "helpUrl": f"https://example.com/rules/{rule_id}",
        "tags": ["wcag2a"],
        "nodes": [{"target": [f"#{i}"], "html": f"<p>{i}</p>"} for i in range(nodes)],
    }


def test_slim_axe_report_keeps_counts_and_is_idempotent():
    report = {"violations": [_rule("image-alt", 3)], "incomplete": [_rule("x", 1)],
              "passes": [_rule("region", 5)], "inapplicable": [_rule("blink", 0)]}

    slim = slim_axe_report(report)

    assert slim["violations"][0]["nodes"] and slim["incomplete"][0]["nodes"]
    assert slim["passes"] == [{"id": "region", "impact": "serious", "description": "region description",
                               "help": "Fix region", "helpUrl": "https://example.com/rules/region",
                               "tags": ["wcag2a"], "node_count": 5}]
    assert slim["inapplicable"][0]["node_count"] == 0
    assert slim_axe_report(slim) == slim
    assert "nodes" in report["passes"][0]  # the input is not mutated


def test_passes_are_stored_without_nodes_but_still_counted(app, make_user, make_site, add_report):
    site = make_site(make_user())
    report = add_report(site, passes=[_rule("region", 5), _rule("html-has-lang", 1)])

    stored = report.report["passes"]
    assert [rule["node_count"] for rule in stored] == [5, 1]
    assert all("nodes" not in rule for rule in stored)
    assert report.report["violations"][0]["nodes"]  # violations keep their nodes
    assert report.report_counts["passes"]["total"] == 2
    assert "inaccessible" not in report.report_counts
    assert set(report.report_counts) == {"violations", "incomplete", "passes"}


def test_markdown_and_pdf_ignore_a_legacy_inaccessible_key(app, make_user, make_site, add_report):
    from utils.markdown import report_to_markdown
    from utils.pdf import generate_pdf

    site = make_site(make_user())
    report = add_report(site, passes=[_rule("region", 5)])
    report.report_counts = {**report.report_counts,
                            "inaccessible": {"total": 9, "critical": 0, "serious": 0, "moderate": 0, "minor": 9}}

    md = report_to_markdown(report)
    assert "Inaccessible" not in md and "| Passes | 1 |" in md
    assert generate_pdf(report)[:4] == b"%PDF"


def test_photo_is_not_loaded_with_the_report(app, make_user, make_site, add_report):
    from models import db
    from models.report import Report

    site = make_site(make_user())
    report = add_report(site, photo=b"\x89PNG\r\n\x1a\nfake")
    db.session.expire_all()

    loaded = db.session.get(Report, report.id)
    assert "photo" in inspect(loaded).unloaded
    assert loaded.report_counts["violations"]["total"] == 1


def test_photo_endpoint_serves_the_png_with_cache_headers(client, make_user, make_site, add_report, jwt_header):
    owner = make_user()
    site = make_site(owner)
    png = b"\x89PNG\r\n\x1a\nfake"
    report = add_report(site, photo=png)

    resp = client.get(f"/api/reports/{report.id}/photo/", headers=jwt_header(owner))
    assert resp.status_code == 200
    assert resp.mimetype == "image/png"
    assert resp.data == png
    assert "private" in resp.headers["Cache-Control"]
    assert resp.headers.get("ETag") and resp.headers.get("Last-Modified")

    again = client.get(
        f"/api/reports/{report.id}/photo/",
        headers={**jwt_header(owner), "If-None-Match": resp.headers["ETag"]},
    )
    assert again.status_code == 304


def test_photo_endpoint_404_without_a_screenshot(client, make_user, make_site, add_report, jwt_header):
    owner = make_user()
    report = add_report(make_site(owner))
    assert client.get(f"/api/reports/{report.id}/photo/", headers=jwt_header(owner)).status_code == 404

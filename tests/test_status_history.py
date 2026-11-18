"""Every status a person gives a finding is kept, with who, why and how."""
import pytest

import models.website as website_models
from models import db
from models.finding import Finding, FindingStatusChange
from services.findings import bulk_set_status, bulk_set_status_ids, record_report_findings


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setattr(website_models, "is_valid_url", lambda url: True)


def _finding(make_user, make_site, add_report):
    owner = make_user("owner")
    site = make_site(owner)
    report = add_report(site)
    record_report_findings(report)
    db.session.commit()
    return owner, site, db.session.query(Finding).filter_by(site_id=site.id).one()


def test_each_change_is_appended_not_overwritten(client, jwt_header, make_user, make_site, add_report):
    owner, site, finding = _finding(make_user, make_site, add_report)
    headers = jwt_header(owner)
    assert client.patch(f"/api/findings/{finding.id}/", json={"status": "accepted", "note": "Vendor widget, ticket 42"},
                        headers=headers).status_code == 200
    assert client.patch(f"/api/findings/{finding.id}/", json={"status": "open"}, headers=headers).status_code == 200

    response = client.get(f"/api/findings/{finding.id}/history/", headers=headers)
    assert response.status_code == 200
    changes = response.get_json()["changes"]
    assert [(c["old_status"], c["new_status"]) for c in changes] == [("open", "accepted"), ("accepted", "open")]
    assert changes[0]["note"] == "Vendor widget, ticket 42" and changes[0]["by"] == "owner"
    assert changes[0]["scope"] == "element" and changes[0]["batch_size"] == 1


def test_history_needs_view_rights(client, jwt_header, make_user, make_site, add_report):
    _, _, finding = _finding(make_user, make_site, add_report)
    stranger = make_user("stranger")
    assert client.get(f"/api/findings/{finding.id}/history/", headers=jwt_header(stranger)).status_code == 403


def test_bulk_changes_record_their_scope(app, make_user, make_site, add_report):
    owner, site, finding = _finding(make_user, make_site, add_report)
    bulk_set_status([site.id], finding.rule_id, "false_positive", "Checked by hand, passes", owner.id)
    bulk_set_status_ids([finding.id], "accepted", "Third-party widget, ticket 7", owner.id)
    db.session.commit()
    changes = db.session.query(FindingStatusChange).order_by(FindingStatusChange.id).all()
    assert [(c.scope, c.batch_size, c.new_status) for c in changes] == [
        ("rule", 1, "false_positive"), ("group", 1, "accepted")]

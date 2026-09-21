"""Website.last_notified records when the website's admin and users were last emailed:
set only when a notification was actually handed over, never when it was skipped."""
import pytest

import mail.emails as emails_mod
import models.website as website_models
from mail.emails import NewWebsiteEmail, ScanFinishedEmail


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setattr(website_models, "is_valid_url", lambda url: True)


def test_forced_scan_email_stamps_last_notified(app, make_user, make_website):
    website = make_website(make_user())
    assert website.last_notified is None

    ScanFinishedEmail(website).send(force=True)

    assert website.last_notified is not None
    assert website.to_dict()["last_notified"]


def test_scan_email_disabled_on_the_website_does_not_stamp(app, make_user, make_website):
    website = make_website(make_user())
    website.should_email = False

    ScanFinishedEmail(website).send()

    assert website.last_notified is None


def test_scan_email_below_thresholds_does_not_stamp(app, make_user, make_website):
    website = make_website(make_user())
    website.should_email = True

    ScanFinishedEmail(website).send()  # no reports at all: nothing worth mailing about

    assert website.last_notified is None


def test_new_website_email_stamps_last_notified(app, make_user, make_website):
    website = make_website(make_user())

    NewWebsiteEmail(website).send()

    assert website.last_notified is not None


def test_failed_delivery_does_not_stamp(app, make_user, make_website, monkeypatch):
    monkeypatch.setattr(emails_mod, "TESTING", False)

    def boom(msg):
        raise RuntimeError("smtp down")

    monkeypatch.setattr(emails_mod.mail, "send", boom)
    website = make_website(make_user())

    ScanFinishedEmail(website).send(force=True)

    assert website.last_notified is None


def test_send_report_email_now_updates_last_notified(client, make_user, make_website, jwt_header):
    admin = make_user("root", is_admin=True)
    website = make_website(admin)

    resp = client.post(f"/api/websites/email/{website.id}/", json={}, headers=jwt_header(admin))
    assert resp.status_code == 200

    resp = client.get(f"/api/websites/{website.id}/", headers=jwt_header(admin))
    assert resp.status_code == 200
    assert resp.get_json()["last_notified"] is not None

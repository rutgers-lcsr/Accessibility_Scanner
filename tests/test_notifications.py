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

    def boom(*args, **kwargs):
        raise RuntimeError("smtp down")

    monkeypatch.setattr(emails_mod.mail, "connect", boom)
    website = make_website(make_user())

    ScanFinishedEmail(website).send(force=True)

    assert website.last_notified is None


def test_send_report_email_now_updates_last_notified(client, make_user, make_website, jwt_header):
    admin = make_user("root", is_admin=True)
    website = make_website(admin)

    resp = client.post(f"/api/websites/email/{website.id}/", json={}, headers=jwt_header(admin))
    assert resp.status_code == 200
    assert resp.get_json()["sent"] == 1

    resp = client.get(f"/api/websites/{website.id}/", headers=jwt_header(admin))
    assert resp.status_code == 200
    assert resp.get_json()["last_notified"] is not None


def test_forced_scan_email_reports_how_many_went_out(app, make_user, make_website):
    owner = make_user("alice")
    member = make_user("bob")
    website = make_website(owner)
    website.users.append(member)
    website.should_email = False
    website.set_subscribed(member, False)

    assert ScanFinishedEmail(website).send(force=True) == 1
    assert website.last_notified is not None

    website.set_subscribed(owner, False)
    website.last_notified = None
    assert ScanFinishedEmail(website).send(force=True) == 0
    assert website.last_notified is None


# --- per-user opt-out ---------------------------------------------------------------


def test_opted_out_user_is_not_a_recipient(app, make_user, make_website):
    owner = make_user("alice")
    member = make_user("bob")
    website = make_website(owner)
    website.users.append(member)

    assert {u.username for u in website.get_recipients()} == {"alice", "bob"}
    website.set_subscribed(member, False)
    assert {u.username for u in website.get_recipients()} == {"alice"}
    assert website.is_subscribed(member) is False and website.is_subscribed(owner) is True
    website.set_subscribed(member, True)
    website.set_subscribed(member, True)  # idempotent
    assert website.is_subscribed(member) is True


def test_each_recipient_gets_their_own_unsubscribe_link(app, make_user, make_website):
    from utils.jwt import decode_jwt_token

    owner = make_user("alice")
    member = make_user("bob")
    website = make_website(owner)
    website.users.append(member)

    sender = ScanFinishedEmail(website)
    sender.send(force=True)

    assert len(sender.messages) == 2
    user_ids = []
    for msg in sender.messages:
        assert len(msg.recipients) == 1
        token = msg.html.split("unsubscribe/?token=")[1].split('"')[0]
        payload = decode_jwt_token(token)
        assert payload["action"] == "unsubscribe" and payload["website_id"] == website.id
        assert "exp" in payload
        user_ids.append(payload["user_id"])
    assert sorted(user_ids) == sorted([owner.id, member.id])
    assert website.last_notified is not None


def test_extra_address_gets_no_unsubscribe_link(app, make_user, make_website):
    website = make_website(make_user())
    sender = ScanFinishedEmail(website)
    sender.send(email="someone@example.org", force=True)

    by_address = {msg.recipients[0]: msg.html for msg in sender.messages}
    assert "unsubscribe/?token=" in by_address[website.admin.email]
    assert "unsubscribe/?token=" not in by_address["someone@example.org"]


def test_expired_unsubscribe_link_is_rejected(client, make_user, make_website):
    from datetime import datetime, timedelta, timezone
    from utils.jwt import generate_jwt_token

    owner = make_user()
    website = make_website(owner)
    token = generate_jwt_token({"action": "unsubscribe", "website_id": website.id, "user_id": owner.id,
                                "exp": datetime.now(timezone.utc) - timedelta(days=1)})
    assert client.get(f"/api/users/unsubscribe/?token={token}").status_code == 401
    assert website.is_subscribed(owner) is True


def test_notification_switch_round_trip(client, make_user, make_website, jwt_header):
    owner = make_user("alice")
    stranger = make_user("carol")
    website = make_website(owner)
    website.should_email = True

    url = f"/api/websites/{website.id}/notifications/"
    assert client.get(url, headers=jwt_header(owner)).get_json() == {"subscribed": True, "website_wide": True}

    resp = client.put(url, json={"subscribed": False}, headers=jwt_header(owner))
    assert resp.status_code == 200 and resp.get_json()["subscribed"] is False
    assert website.should_email is True
    assert client.get(url, headers=jwt_header(owner)).get_json()["subscribed"] is False

    assert client.put(url, json={"subscribed": True}, headers=jwt_header(owner)).get_json()["subscribed"] is True
    assert client.put(url, json={"subscribed": "no"}, headers=jwt_header(owner)).status_code == 400
    assert client.get(url, headers=jwt_header(stranger)).status_code == 403  # private website
    assert client.get(url).status_code == 401

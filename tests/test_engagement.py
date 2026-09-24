"""Engagement: when a website's own people last opened its page, and the last login, on
the admin Owners API and its CSV."""
import csv
import io
from datetime import datetime

import pytest

import models.website as website_models
from models import db
from models.notifications import WebsiteView


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setattr(website_models, "is_valid_url", lambda url: True)


def test_views_are_recorded_for_the_websites_own_people_only(client, make_user, make_website, jwt_header):
    owner = make_user("alice")
    member = make_user("bob")
    admin = make_user("root", is_admin=True)
    website = make_website(owner, public=True)
    website.users.append(member)
    db.session.commit()

    for user in (owner, member, admin):
        assert client.get(f"/api/websites/{website.id}/", headers=jwt_header(user)).status_code == 200
    assert client.get(f"/api/websites/{website.id}/").status_code == 200  # anonymous, public

    views = WebsiteView.by_website([website.id])[website.id]
    assert set(views) == {owner.id, member.id}


def test_a_view_is_upserted(app, make_user, make_website):
    website = make_website(make_user())

    WebsiteView.touch(website.admin_id, website.id, now=datetime(2026, 9, 1, 8, 0))
    WebsiteView.touch(website.admin_id, website.id, now=datetime(2026, 9, 2, 9, 0))

    assert db.session.query(WebsiteView).count() == 1
    assert WebsiteView.by_website([website.id])[website.id][website.admin_id] == datetime(2026, 9, 2, 9, 0)


def test_owners_api_and_csv_expose_login_views_and_reminders(client, make_user, make_website, jwt_header):
    admin = make_user("root", is_admin=True)
    alice = make_user("alice")
    alice.last_login = datetime(2026, 9, 3, 8, 0)
    website = make_website(alice)
    website.reminder_count = 2
    website.last_reminded_at = datetime(2026, 9, 10)
    website.escalated_at = datetime(2026, 9, 20)
    db.session.commit()
    WebsiteView.touch(alice.id, website.id, now=datetime(2026, 9, 5, 9, 0))

    owner = client.get("/api/dashboard/owners/", headers=jwt_header(admin)).get_json()["owners"][0]
    assert owner["last_login"] == "2026-09-03T08:00:00Z" and owner["last_viewed"] == "2026-09-05T09:00:00Z"
    row = owner["websites"][0]
    assert row["last_viewed"] == "2026-09-05T09:00:00Z"
    assert row["reminders"] == {"attention_since": None, "last_reminded_at": "2026-09-10T00:00:00Z", "count": 2,
                                "escalated_at": "2026-09-20T00:00:00Z"}

    resp = client.get("/api/dashboard/owners/?format=csv", headers=jwt_header(admin))
    rows = list(csv.reader(io.StringIO(resp.get_data(as_text=True))))
    assert rows[0][-5:] == ["last_login", "last_viewed", "reminders_sent", "last_reminded", "escalated_at"]
    assert rows[1][-5:] == ["2026-09-03T08:00:00Z", "2026-09-05T09:00:00Z", "2", "2026-09-10T00:00:00Z", "2026-09-20T00:00:00Z"]


def test_cas_login_stamps_last_login(client, app):
    from models.user import User

    headers = {"x-cas-user": "alice", "x-cas-server": "https://cas.rutgers.edu/cas",
               "X-Internal-Secret": app.config["INTERNAL_AUTH_SECRET"]}
    assert client.get("/api/auth/cas", headers=headers).status_code == 200

    user = db.session.query(User).filter_by(username="alice").one()
    assert user.last_login is not None
    assert user.to_dict()["last_login"] == user.last_login

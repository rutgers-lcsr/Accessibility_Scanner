"""Unsubscribing: the link shows a confirmation and only a POST opts out; a token without
a website covers every website the person is emailed about; one-click POSTs work."""
import pytest

import models.website as website_models
from models import db
from utils.jwt import generate_jwt_token


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setattr(website_models, "is_valid_url", lambda url: True)


def test_get_shows_the_confirmation_and_changes_nothing(client, make_user, make_website):
    owner = make_user()
    website = make_website(owner)
    token = generate_jwt_token({"action": "unsubscribe", "website_id": website.id, "user_id": owner.id})

    resp = client.get(f"/api/users/unsubscribe/?token={token}")

    assert resp.status_code == 200
    page = resp.get_data(as_text=True)
    assert "Stop emails about" in page and website.url in page and f'value="{token}"' in page
    assert website.is_subscribed(owner) is True


def test_post_from_the_form_opts_out(client, make_user, make_website):
    owner = make_user()
    website = make_website(owner)
    token = generate_jwt_token({"action": "unsubscribe", "website_id": website.id, "user_id": owner.id})

    resp = client.post("/api/users/unsubscribe/", data={"token": token})

    assert resp.status_code == 200 and "no longer receive" in resp.get_data(as_text=True)
    assert website.is_subscribed(owner) is False


def test_one_click_post_with_the_query_token_opts_out(client, make_user, make_website):
    owner = make_user()
    website = make_website(owner)
    token = generate_jwt_token({"action": "unsubscribe", "website_id": website.id, "user_id": owner.id})

    resp = client.post(f"/api/users/unsubscribe/?token={token}", data="List-Unsubscribe=One-Click",
                       content_type="application/x-www-form-urlencoded")

    assert resp.status_code == 200
    assert website.is_subscribed(owner) is False


def test_a_token_without_a_website_silences_every_website_of_the_person(client, make_user, make_website):
    alice = make_user("alice")
    bob = make_user("bob")
    mine = make_website(alice, base="https://one.example.com")
    shared = make_website(bob, base="https://two.example.com")
    shared.users.append(alice)
    other = make_website(bob, base="https://three.example.com")
    db.session.commit()
    token = generate_jwt_token({"action": "unsubscribe", "website_id": None, "user_id": alice.id})

    page = client.get(f"/api/users/unsubscribe/?token={token}").get_data(as_text=True)
    assert "your 2 websites" in page and mine.url in page and shared.url in page and other.url not in page

    assert client.post("/api/users/unsubscribe/", data={"token": token}).status_code == 200
    assert mine.is_subscribed(alice) is False and shared.is_subscribed(alice) is False
    assert shared.is_subscribed(bob) is True and other.is_subscribed(bob) is True


def test_bad_tokens_are_refused_on_post_too(client, make_user, make_website):
    website = make_website(make_user())
    assert client.post("/api/users/unsubscribe/", data={"token": "garbage"}).status_code == 401
    assert client.post("/api/users/unsubscribe/").status_code == 400
    legacy = generate_jwt_token({"action": "subscribe", "website_id": website.id})
    assert client.post("/api/users/unsubscribe/", data={"token": legacy}).status_code == 400

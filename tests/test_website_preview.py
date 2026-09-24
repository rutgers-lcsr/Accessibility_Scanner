"""GET /api/websites/<id>/preview/: a small JPEG of the top of the home page's latest
screenshot, who may see it, and that the browser can keep it."""
import io

import pytest

import models.website as website_models
from services.preview import PREVIEW_HEIGHT, PREVIEW_WIDTH, home_site


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setattr(website_models, "is_valid_url", lambda url: True)


def _png(width=1280, height=3000, color="white"):
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buffer, format="PNG")
    return buffer.getvalue()


def _size(data):
    from PIL import Image

    image = Image.open(io.BytesIO(data))
    return image.format, image.size


def test_preview_is_the_top_of_the_home_page_screenshot(client, make_user, make_website, add_site, add_report, jwt_header):
    owner = make_user()
    website = make_website(owner, base="https://example.com")
    home = add_site(website, page="/")
    about = add_site(website, page="/about")
    add_report(home, photo=_png(1280, 3000, "white"))
    add_report(about, photo=_png(1280, 3000, "black"))  # newer, but not the home page

    resp = client.get(f"/api/websites/{website.id}/preview/", headers=jwt_header(owner))

    assert resp.status_code == 200
    assert resp.mimetype == "image/jpeg"
    fmt, (width, height) = _size(resp.data)
    assert fmt == "JPEG" and width == PREVIEW_WIDTH and height <= PREVIEW_HEIGHT
    assert len(resp.data) < 20_000  # a thumbnail, not the page
    assert "private" in resp.headers["Cache-Control"] and resp.headers.get("ETag")

    again = client.get(
        f"/api/websites/{website.id}/preview/",
        headers={**jwt_header(owner), "If-None-Match": resp.headers["ETag"]},
    )
    assert again.status_code == 304


def test_preview_falls_back_to_the_shortest_page_url(app, make_user, make_website, add_site):
    website = make_website(make_user(), base="https://example.com")
    add_site(website, page="/courses/cs440/")
    add_site(website, page="/courses/")

    assert home_site(website).url == "https://example.com/courses/"


def test_preview_404_without_a_screenshot(client, make_user, make_website, add_site, add_report, jwt_header):
    owner = make_user()
    website = make_website(owner, base="https://example.com")
    assert client.get(f"/api/websites/{website.id}/preview/", headers=jwt_header(owner)).status_code == 404
    add_report(add_site(website, page="/"))  # a report, but no photo
    assert client.get(f"/api/websites/{website.id}/preview/", headers=jwt_header(owner)).status_code == 404


def test_preview_follows_website_visibility(client, make_user, make_website, add_site, add_report, jwt_header):
    owner = make_user("alice")
    stranger = make_user("bob")
    website = make_website(owner, base="https://example.com")
    add_report(add_site(website, page="/"), photo=_png())

    assert client.get(f"/api/websites/{website.id}/preview/").status_code == 403
    assert client.get(f"/api/websites/{website.id}/preview/", headers=jwt_header(stranger)).status_code == 403

    website.public = True
    website_models.db.session.commit()
    assert client.get(f"/api/websites/{website.id}/preview/").status_code == 200

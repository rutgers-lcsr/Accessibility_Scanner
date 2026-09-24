"""A website's hover preview: a small JPEG of the top of its home page, cut from the
full-page screenshot of that page's latest report."""
import io

from sqlalchemy import func

from models import db
from models.report import Report
from models.website import Site, Website
from utils.urls import normalize_url

PREVIEW_WIDTH = 480
PREVIEW_HEIGHT = 300  # the top of a 1280px-wide page, scaled: roughly above the fold


def home_site(website: Website):
    """The website's home page: the site whose URL is the website's, else the shortest."""
    sites = website.sites.with_entities(Site.id, Site.url).all()
    if not sites:
        return None
    wanted = normalize_url(website.url)
    for site in sites:
        if normalize_url(site.url) == wanted:
            return site
    return min(sites, key=lambda site: (len(site.url), site.url))


def latest_report_with_photo(site_id: int):
    """``(id, timestamp)`` of the page's newest report that still has a screenshot."""
    return (
        db.session.query(Report.id, Report.timestamp)
        .filter(Report.site_id == site_id, Report.photo.isnot(None))
        .order_by(Report.timestamp.desc(), Report.id.desc())
        .first()
    )


def preview_jpeg(photo: bytes) -> bytes:
    """The top of a full-page PNG screenshot as a PREVIEW_WIDTH-wide JPEG."""
    from PIL import Image

    image = Image.open(io.BytesIO(photo))
    width, height = image.size
    image = image.crop((0, 0, width, min(height, width * PREVIEW_HEIGHT // PREVIEW_WIDTH)))
    image.thumbnail((PREVIEW_WIDTH, PREVIEW_HEIGHT))
    buffer = io.BytesIO()
    image.convert('RGB').save(buffer, format='JPEG', quality=80, optimize=True)
    return buffer.getvalue()

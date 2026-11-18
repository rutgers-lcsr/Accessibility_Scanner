"""The website header's scan age: pages rescanned on their own after the last full scan."""
from datetime import datetime, timedelta


def test_page_rescans_counts_pages_newer_than_the_full_scan(app, make_user, make_website, add_site):
    from models import db

    owner = make_user('owner')
    website = make_website(owner)
    full = datetime(2026, 9, 28, 2, 0)
    website.last_scanned = full
    in_crawl, rescanned, never = add_site(website, '/a'), add_site(website, '/b'), add_site(website, '/c')
    in_crawl.last_scanned = full + timedelta(hours=3)  # part of the full scan
    rescanned.last_scanned = datetime(2026, 11, 17, 14, 13)
    never.last_scanned = None
    db.session.commit()

    assert website.page_rescans() == {'count': 1, 'latest': '2026-11-17T14:13:00Z'}
    assert website.to_dict(with_report=True)['page_rescans']['count'] == 1
    assert website.to_dict()['page_rescans'] is None


def test_page_rescans_without_a_full_scan(app, make_user, make_website):
    website = make_website(make_user('owner'))
    assert website.page_rescans() == {'count': 0, 'latest': None}

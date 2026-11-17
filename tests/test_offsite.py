"""Pages whose scan ended on another site (a login page that redirects to CAS) are not
the owner's to fix: they leave the website's counts, Fix first and the findings."""
from datetime import datetime, timedelta, timezone

from utils.urls import is_offsite


def test_offsite_compares_hosts_ignoring_www():
    assert not is_offsite('https://example.com/login', 'https://example.com')
    assert not is_offsite('https://example.com/a', 'https://www.example.com')
    assert not is_offsite('https://www.example.com/a', 'https://example.com')
    assert is_offsite('https://example.com/login', 'https://cas.rutgers.edu')
    assert not is_offsite('https://example.com/a', '')
    assert not is_offsite('https://example.com/a', None)


def _record(add_report, site, **kwargs):
    from models import db
    from services.findings import record_report_findings

    report = add_report(site, **kwargs)
    record_report_findings(report)
    db.session.commit()
    return report


def test_offsite_report_records_no_findings_and_counts_nothing(make_user, make_site, add_report):
    from models.finding import Finding
    from services.history import effective_counts

    site = make_site(make_user('bob'), page='/login')
    report = _record(add_report, site, base_url='https://cas.rutgers.edu')

    assert Finding.query.filter_by(site_id=site.id).count() == 0
    assert effective_counts(report.report_counts, report.suppressed_counts)['violations']['total'] == 0


def test_offsite_page_leaves_latest_and_fix_first(make_user, make_site, add_report):
    from services.findings import fix_first, latest_report_ids

    site = make_site(make_user('bob'), page='/login')
    now = datetime.now(timezone.utc)
    _record(add_report, site, when=now - timedelta(days=2))  # on-site scan first
    _record(add_report, site, when=now, base_url='https://cas.rutgers.edu')

    assert latest_report_ids([site.id]) == {}
    assert fix_first([site.id])['rules'] == []


def test_website_aggregate_and_counts_skip_offsite_pages(make_user, make_website, add_site, add_report):
    owner = make_user('bob')
    website = make_website(owner)
    own = add_site(website, page='/about')
    login = add_site(website, page='/login')
    _record(add_report, own)
    _record(add_report, login, base_url='https://cas.rutgers.edu')

    rule = website.get_report()['violations'][0]
    assert [r['url'] for r in rule['reports']] == [own.url]
    assert website.get_report_counts()['violations']['total'] == 1


def test_pages_list_says_which_site_was_scanned(make_user, make_site, add_report):
    site = make_site(make_user('bob'), page='/login')
    _record(add_report, site, base_url='https://cas.rutgers.edu')
    assert site.get_recent_report()['scanned_host'] == 'cas.rutgers.edu'


def test_dashboard_overview_leaves_offsite_pages_out(make_user, make_website, add_site, add_report):
    """The dashboard's audited pages, top rules and manual-check counts agree with the
    website page: a scan that ended on another site counts for nothing, and is reported
    on its own."""
    from services.overview import build_overview

    website = make_website(make_user('bob'))
    own = add_site(website, page='/about')
    login = add_site(website, page='/login')
    _record(add_report, own, violations=[])
    _record(add_report, login, base_url='https://cas.rutgers.edu')

    overview = build_overview([website], top=5)
    totals = overview['totals']
    assert totals['pages_audited'] == 1
    assert totals['pages_offsite'] == 1
    assert totals['violations']['total'] == 0
    assert overview['top_rules'] == []


def test_what_changed_leaves_offsite_pages_out(make_user, make_website, add_site, add_report):
    from datetime import datetime, timedelta, timezone

    from services.findings import changes_for_sites

    website = make_website(make_user('bob'))
    login = add_site(website, page='/login')
    now = datetime.now(timezone.utc)
    _record(add_report, login, when=now - timedelta(days=1))  # on-site: one open finding
    _record(add_report, login, when=now, base_url='https://cas.rutgers.edu')

    changes = changes_for_sites([login.id])
    assert changes['open_count'] == 0 and changes['still_open'] == []
    assert changes['current']['total'] == 0

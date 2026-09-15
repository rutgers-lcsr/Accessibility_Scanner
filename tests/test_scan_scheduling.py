"""Scheduling: a PENDING task id only counts as running while it is recent, a stale
Site.scanning flag expires, and the periodic task records task ids like a manual scan."""
import types
from datetime import datetime, timedelta, timezone

import pytest

import services.scan as scan_service


class _FakeAsyncResult:
    def __init__(self, state):
        self.state = state


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _website(make_user, make_site):
    return make_site(make_user()).websites.first()


@pytest.mark.parametrize(
    "state,expected",
    [("STARTED", True), ("PROGRESS", True), ("RETRY", True), ("SUCCESS", False), ("FAILURE", False)],
)
def test_task_state_decides_in_progress(app, make_user, make_site, monkeypatch, state, expected):
    from models import db

    website = _website(make_user, make_site)
    website.current_task_id = "t"
    db.session.commit()
    monkeypatch.setattr(scan_service.scan_website_task, "AsyncResult", lambda tid: _FakeAsyncResult(state))

    assert scan_service.scan_in_progress(website) is expected


def test_pending_is_trusted_only_while_recent(app, make_user, make_site, monkeypatch):
    from models import db

    website = _website(make_user, make_site)
    website.current_task_id = "t"
    monkeypatch.setattr(scan_service.scan_website_task, "AsyncResult", lambda tid: _FakeAsyncResult("PENDING"))

    website.scan_queued_at = None  # unknown id, e.g. queued before this column existed
    db.session.commit()
    assert scan_service.scan_in_progress(website) is False

    website.scan_queued_at = _utcnow() - timedelta(hours=1)
    db.session.commit()
    assert scan_service.scan_in_progress(website) is True

    website.scan_queued_at = _utcnow() - scan_service.STALE_AFTER - timedelta(minutes=1)
    db.session.commit()
    assert scan_service.scan_in_progress(website) is False


def test_no_task_id_means_not_in_progress(app, make_user, make_site, monkeypatch):
    website = _website(make_user, make_site)
    website.current_task_id = None

    def boom(task_id):
        raise AssertionError("AsyncResult must not be consulted without a task id")

    monkeypatch.setattr(scan_service.scan_website_task, "AsyncResult", boom)
    assert scan_service.scan_in_progress(website) is False


def test_site_scanning_flag_goes_stale(app, make_user, make_site):
    site = make_site(make_user())

    site.scanning = False
    assert scan_service.site_scan_in_progress(site) is False

    site.scanning = True
    site.scan_queued_at = None
    assert scan_service.site_scan_in_progress(site) is False

    site.scan_queued_at = _utcnow() - timedelta(minutes=5)
    assert scan_service.site_scan_in_progress(site) is True

    site.scan_queued_at = _utcnow() - scan_service.STALE_AFTER - timedelta(minutes=1)
    assert scan_service.site_scan_in_progress(site) is False


def test_queueing_records_when_the_task_was_queued(app, make_user, make_site, monkeypatch):
    website = _website(make_user, make_site)
    monkeypatch.setattr(scan_service.scan_website_task, "delay", lambda url: types.SimpleNamespace(id="q-1"))

    task_id, queued = scan_service.queue_website_scan(website)
    assert (task_id, queued) == ("q-1", True)
    assert website.current_task_id == website.last_task_id == "q-1"
    assert website.scan_queued_at is not None
    assert _utcnow() - website.scan_queued_at < timedelta(minutes=1)


# --- periodic task -------------------------------------------------------------------


def test_periodic_check_queues_due_websites_and_records_task(app, make_user, make_site, monkeypatch):
    from models import db
    from scanner.tasks import check_and_queue_scans

    website = _website(make_user, make_site)
    website.active = True
    website.last_scanned = None
    db.session.commit()
    monkeypatch.setattr(scan_service.scan_website_task, "delay", lambda url: types.SimpleNamespace(id="beat-1"))

    result = check_and_queue_scans.run()

    assert result == {"checked": 1, "queued": 1}
    assert website.current_task_id == "beat-1"
    assert website.last_task_id == "beat-1"  # status polling can resolve scheduled scans too
    assert website.scan_queued_at is not None


def test_periodic_check_skips_running_and_not_due_websites(app, make_user, make_site, monkeypatch):
    import models.website as website_models
    from models import db
    from scanner.tasks import check_and_queue_scans

    # Domain/Website creation resolves hostnames; keep this test offline.
    monkeypatch.setattr(website_models, "is_valid_url", lambda url: True)
    owner = make_user()
    running = make_site(owner, base="https://running.example").websites.first()
    running.active = True
    running.last_scanned = None
    running.current_task_id = "busy"
    running.scan_queued_at = _utcnow()

    fresh = make_site(owner, base="https://fresh.example").websites.first()
    fresh.active = True
    fresh.rate_limit = 30
    fresh.last_scanned = datetime.now()
    db.session.commit()

    monkeypatch.setattr(scan_service.scan_website_task, "AsyncResult", lambda tid: _FakeAsyncResult("PROGRESS"))
    monkeypatch.setattr(
        scan_service.scan_website_task,
        "delay",
        lambda url: (_ for _ in ()).throw(AssertionError(f"should not queue {url}")),
    )

    assert check_and_queue_scans.run() == {"checked": 2, "queued": 0}

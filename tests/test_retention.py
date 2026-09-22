"""Report retention: the plan (recent kept, monthly survivors, old deleted, latest never
touched), batched application, the dry run, the beat task's switch, the CLI, and the
slimming backfill."""
from datetime import datetime, timedelta, timezone

import pytest

import models.website as website_models
from services.maintenance import apply_retention, plan_retention, slim_stored_reports


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setattr(website_models, "is_valid_url", lambda url: True)


def _days_ago(n):
    return datetime.now(timezone.utc) - timedelta(days=n)


def test_plan_keeps_recent_thins_to_one_per_month_and_deletes_old(app, make_user, make_site, add_report):
    site = make_site(make_user())
    kept_recent = [add_report(site, when=_days_ago(d), photo=b"png") for d in (0, 3, 30, 60, 89)]
    # 100 and 110 days ago share a month only if the calendar agrees; use far-apart months
    m1_new = add_report(site, when=_days_ago(100), photo=b"png")
    m1_old = add_report(site, when=_days_ago(100) - timedelta(days=5), photo=b"png")  # same month as m1_new? not guaranteed
    m2 = add_report(site, when=_days_ago(200), photo=b"png")
    too_old = [add_report(site, when=_days_ago(d), photo=b"png") for d in (400, 500)]

    plan = plan_retention(keep_days=90, max_days=365)

    assert set(plan.delete_ids) >= {r.id for r in too_old}
    assert not ({r.id for r in kept_recent} & set(plan.delete_ids))
    assert kept_recent[0].id not in plan.strip_photo_ids  # the latest keeps its screenshot
    survivors = {m1_new.id, m1_old.id, m2.id} - set(plan.delete_ids)
    assert m2.id in survivors and m1_new.id in survivors
    # every survivor in the monthly band loses its screenshot, and months are unique
    assert survivors <= set(plan.strip_photo_ids)
    months = {r.timestamp.strftime("%Y-%m") for r in (m1_new, m1_old, m2) if r.id in survivors}
    assert len(months) == len(survivors)
    assert plan.per_site[0]["site_id"] == site.id and plan.per_site[0]["url"] == site.url


def test_the_latest_report_is_never_deleted_even_when_old(app, make_user, make_site, add_report):
    site = make_site(make_user())
    only = add_report(site, when=_days_ago(3 * 365), photo=b"png")

    plan = plan_retention(keep_days=90, max_days=365)

    assert plan.delete_ids == [] and plan.strip_photo_ids == []
    assert only.id not in plan.delete_ids


def test_apply_deletes_in_batches_and_the_dry_run_changes_nothing(app, make_user, make_site, add_report):
    from models import db
    from models.report import Report

    site = make_site(make_user())
    latest_id = add_report(site, when=_days_ago(1)).id
    old_ids = [add_report(site, when=_days_ago(400 + i), photo=b"png").id for i in range(7)]
    site_id = site.id
    plan = plan_retention(keep_days=90, max_days=365)
    assert sorted(plan.delete_ids) == sorted(old_ids)

    assert apply_retention(plan, batch_size=2, dry_run=True) == {"deleted": 7, "photos_stripped": 0, "dry_run": True}
    assert db.session.query(Report).count() == 8

    result = apply_retention(plan, batch_size=2)
    assert result["deleted"] == 7
    db.session.expunge_all()
    assert [r.id for r in db.session.query(Report).all()] == [latest_id]
    assert db.session.get(website_models.Site, site_id).get_recent_report()["id"] == latest_id
    assert all(db.session.get(Report, report_id) is None for report_id in old_ids)


def test_screenshots_are_dropped_from_monthly_survivors_only(app, make_user, make_site, add_report):
    from models import db
    from models.report import Report

    site = make_site(make_user())
    latest = add_report(site, when=_days_ago(1), photo=b"latest")
    survivor = add_report(site, when=_days_ago(200), photo=b"old")
    plan = plan_retention(keep_days=90, max_days=365)
    assert plan.strip_photo_ids == [survivor.id]

    apply_retention(plan)
    db.session.expire_all()
    assert db.session.query(Report.photo).filter(Report.id == survivor.id).scalar() is None
    assert db.session.query(Report.photo).filter(Report.id == latest.id).scalar() == b"latest"


def test_prune_task_respects_the_setting(app, make_user, make_site, add_report):
    from models import db
    from models.report import Report
    from models.settings import Settings
    from scanner.tasks import prune_reports

    site = make_site(make_user())
    add_report(site, when=_days_ago(1))
    add_report(site, when=_days_ago(400))

    Settings.set("retention_enabled", "false")
    assert prune_reports.run() == {"applied": False, "deleted": 0, "photos_stripped": 0, "sites": 1}
    assert db.session.query(Report).count() == 2

    Settings.set("retention_enabled", "true")
    assert prune_reports.run() == {"applied": True, "deleted": 1, "photos_stripped": 0, "sites": 1}
    assert db.session.query(Report).count() == 1


def test_cli_dry_run_prints_the_plan_and_deletes_nothing(app, make_user, make_site, add_report):
    from models import db
    from models.report import Report

    site = make_site(make_user())
    add_report(site, when=_days_ago(1))
    add_report(site, when=_days_ago(400))

    result = app.test_cli_runner().invoke(args=["maintenance", "retention", "--dry-run"])

    assert result.exit_code == 0, result.output
    assert "would delete 1" in result.output and "TOTAL: 1 reports would be deleted" in result.output
    assert db.session.query(Report).count() == 2


def test_slim_backfill_rewrites_only_old_style_rows(app, make_user, make_site, add_report):
    from models import db
    from models.report import Report

    site = make_site(make_user())
    slim_id = add_report(site, passes=[{"id": "region", "impact": "moderate", "nodes": [{"target": ["#a"]}]}]).id
    legacy = add_report(site)
    legacy_id, legacy_counts = legacy.id, dict(legacy.report_counts)
    db.session.execute(
        Report.__table__.update().where(Report.id == legacy_id).values(
            report={"violations": [], "incomplete": [], "passes": [{"id": "html-has-lang", "impact": "serious", "nodes": [{"target": ["html"], "html": "<html>"}]}]},
            report_counts={**legacy_counts, "inaccessible": {"total": 0}},
        )
    )
    db.session.commit()
    db.session.expunge_all()

    assert slim_stored_reports(dry_run=True) == {"checked": 2, "rewritten": 1, "dry_run": True}
    assert slim_stored_reports() == {"checked": 2, "rewritten": 1, "dry_run": False}
    rewritten = db.session.get(Report, legacy_id)
    assert rewritten.report["passes"] == [{"id": "html-has-lang", "impact": "serious", "node_count": 1}]
    assert "inaccessible" not in rewritten.report_counts
    assert db.session.get(Report, slim_id).report["passes"][0]["node_count"] == 1
    assert slim_stored_reports()["rewritten"] == 0


def test_beat_schedules_the_pruning():
    from celery_app import celery

    assert celery.conf.beat_schedule["prune-reports"]["task"] == "scanner.tasks.prune_reports"

"""services.overview: the shared latest-report aggregation, including the "as of a
moment" variant the emails and digest use to compare then with now."""
from datetime import datetime, timedelta, timezone

import pytest

import models.website as website_models
from services.overview import IMPACT_ORDER, build_overview, latest_reports, sites_of


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setattr(website_models, "is_valid_url", lambda url: True)


def _rule(rule_id, impact, nodes=1):
    return {
        "id": rule_id,
        "impact": impact,
        "help": f"Fix {rule_id}",
        "helpUrl": f"https://example.com/rules/{rule_id}",
        "nodes": [{"target": [f"#{i}"], "html": "<div>"} for i in range(nodes)],
    }


def test_latest_reports_picks_the_newest_or_the_newest_before_a_moment(app, make_user, make_website, add_site, add_report):
    now = datetime.now(timezone.utc)
    website = make_website(make_user())
    home = add_site(website, page="/")
    old = add_report(home, when=now - timedelta(days=3), violations=[_rule("image-alt", "critical", 2)])
    new = add_report(home, when=now, violations=[_rule("color-contrast", "serious")])

    latest = latest_reports([website.id])
    assert latest[home.id].id == new.id
    assert latest[home.id].url == home.url

    then = latest_reports([website.id], before=(now - timedelta(days=1)).replace(tzinfo=None))
    assert then[home.id].id == old.id

    assert latest_reports([website.id], before=(now - timedelta(days=10)).replace(tzinfo=None)) == {}
    assert latest_reports([]) == {}


def test_build_overview_totals_rows_and_top_rules(app, make_user, make_website, add_site, add_report):
    now = datetime.now(timezone.utc)
    owner = make_user()
    website = make_website(owner)
    website.last_scan_status = "completed"
    website.last_scanned = now
    home = add_site(website, page="/")
    about = add_site(website, page="/about")
    add_report(home, when=now - timedelta(days=3), violations=[_rule("image-alt", "critical", 2)])
    add_report(home, when=now, violations=[_rule("color-contrast", "serious")])
    add_report(about, when=now, violations=[_rule("color-contrast", "serious", 3), _rule("label", "critical")])
    empty = make_website(owner, base="https://empty.example")

    overview = build_overview([website, empty], top=5)

    totals = overview["totals"]
    assert totals["websites"] == 2 and totals["pages"] == 2 and totals["pages_audited"] == 2
    assert totals["violations"]["total"] == 3  # rules on the latest report of each page
    assert totals["scan_status"] == {"completed": 1, "never": 1}

    rows = overview["websites"]
    assert [row["url"] for row in rows] == [website.url, empty.url]  # worst first
    assert rows[0]["violations"]["critical"] == 1 and rows[1]["pages"] == 0

    top = overview["top_rules"]
    assert [rule["id"] for rule in top] == ["label", "color-contrast"]  # most severe first
    assert top[1]["pages"] == 2 and top[1]["occurrences"] == 4
    assert sites_of([website.id])[website.id] == {home.id, about.id}
    assert IMPACT_ORDER["critical"] < IMPACT_ORDER["minor"]


def test_build_overview_without_top_rules(app, make_user, make_website, add_site, add_report):
    website = make_website(make_user())
    add_report(add_site(website), violations=[_rule("image-alt", "critical")])

    overview = build_overview([website], top=0)

    assert overview["top_rules"] == []
    assert overview["websites"][0]["violations"]["critical"] == 1

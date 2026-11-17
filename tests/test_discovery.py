"""Site discovery: host cleaning, the certificate transparency parse, gathering from
crawled links, probing, tracked hosts, the endpoints and the weekly task."""
import json
import types
from datetime import datetime, timedelta

import pytest

import models.website as website_models
import services.discovery as discovery_mod
from models import db
from models.discovery import DiscoveredHost
from models.inventory import ThirdPartyHost
from models.link import Link
from models.website import Domain
from services.discovery import clean_host, ct_hosts, discovered_rows, run_discovery, under


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setattr(website_models, "is_valid_url", lambda url: True)


def _probe(host):
    live = host.startswith("www") or host.startswith("lab")
    return {"resolves": True, "http_status": 200 if live else None, "final_url": f"https://{host}/" if live else None,
            "title": f"{host} home" if live else None, "error": None if live else "ConnectionError"}


def test_clean_host_and_under():
    assert clean_host("*.Lab.CS.example.edu.") == "lab.cs.example.edu"
    assert clean_host("not a host") is None
    assert clean_host("user@example.edu") is None
    assert under("lab.cs.example.edu", "cs.example.edu")
    assert under("cs.example.edu", "cs.example.edu")
    assert not under("evil-cs.example.edu", "cs.example.edu")
    assert not under("example.edu", "cs.example.edu")


def test_ct_hosts_parses_crtsh(monkeypatch):
    payload = [
        {"name_value": "cs.example.edu\nwww.cs.example.edu"},
        {"name_value": "*.lab.cs.example.edu"},
        {"name_value": "math.example.edu"},  # another department: not ours
        {"name_value": "foo@cs.example.edu"},  # an email SAN
    ]
    seen = {}

    def fake_get(url, params, timeout, headers):
        seen["params"] = params
        return types.SimpleNamespace(text=json.dumps(payload), raise_for_status=lambda: None)

    monkeypatch.setattr(discovery_mod.requests, "get", fake_get)
    assert ct_hosts("cs.example.edu") == {"cs.example.edu", "www.cs.example.edu", "lab.cs.example.edu"}
    assert seen["params"] == {"q": "%.cs.example.edu", "output": "json"}


def _domain(name="cs.example.edu"):
    domain = Domain(domain=name)
    db.session.add(domain)
    db.session.commit()
    return domain


def test_run_discovery_merges_sources_probes_and_marks_tracked(app, make_user, make_website, monkeypatch):
    domain = _domain()
    owner = make_user()
    website = make_website(owner, base="https://www.cs.example.edu")
    now = datetime(2026, 11, 1)
    db.session.add(Link(website_id=website.id, url="https://lab.cs.example.edu/people", first_seen=now, last_seen=now))
    db.session.add(Link(website_id=website.id, url="https://math.example.edu/", first_seen=now, last_seen=now))
    db.session.add(ThirdPartyHost(website_id=website.id, host="cdn.cs.example.edu", kinds="script", page_count=1,
                                  first_seen=now, last_seen=now))
    db.session.commit()
    monkeypatch.setattr(discovery_mod, "ct_hosts", lambda name: {"www.cs.example.edu", "lab.cs.example.edu", "old.cs.example.edu"})
    probed = []
    monkeypatch.setattr(discovery_mod, "probe_host", lambda host: probed.append(host) or _probe(host))

    result = run_discovery(domain.id, now)

    assert result == {"found": 4, "new": 4, "probed": 3, "ct_error": None}
    assert "www.cs.example.edu" not in probed  # already a website
    rows = {row["host"]: row for row in discovered_rows(domain.id)}
    assert set(rows) == {"www.cs.example.edu", "lab.cs.example.edu", "old.cs.example.edu", "cdn.cs.example.edu"}
    assert rows["lab.cs.example.edu"]["sources"] == ["ct", "links"]
    assert rows["lab.cs.example.edu"]["title"] == "lab.cs.example.edu home"
    assert rows["www.cs.example.edu"]["status"] == "tracked" and rows["www.cs.example.edu"]["website_id"] == website.id
    assert rows["old.cs.example.edu"]["http_status"] is None
    assert db.session.get(Domain, domain.id).discovered_at == now

    # A second run soon after probes nothing new; a week later it re-probes.
    probed.clear()
    assert run_discovery(domain.id, now + timedelta(days=1))["probed"] == 0
    assert run_discovery(domain.id, now + timedelta(days=8))["probed"] == 3


def test_ct_failure_is_reported_and_links_still_used(app, make_user, make_website, monkeypatch):
    domain = _domain()
    website = make_website(make_user(), base="https://www.cs.example.edu")
    now = datetime(2026, 11, 1)
    db.session.add(Link(website_id=website.id, url="https://lab.cs.example.edu/", first_seen=now, last_seen=now))
    db.session.commit()

    def boom(name):
        raise TimeoutError("crt.sh timed out")

    monkeypatch.setattr(discovery_mod, "ct_hosts", boom)
    monkeypatch.setattr(discovery_mod, "probe_host", _probe)
    result = run_discovery(domain.id, now)
    assert result["ct_error"].startswith("TimeoutError") and result["new"] == 1
    assert db.session.get(Domain, domain.id).discovery_error.startswith("TimeoutError")


def test_ignored_hosts_are_not_probed(app, monkeypatch):
    domain = _domain()
    now = datetime(2026, 11, 1)
    db.session.add(DiscoveredHost(domain_id=domain.id, host="old.cs.example.edu", status="ignored",
                                  first_seen=now, last_seen=now))
    db.session.commit()
    monkeypatch.setattr(discovery_mod, "ct_hosts", lambda name: {"old.cs.example.edu"})
    monkeypatch.setattr(discovery_mod, "probe_host", lambda host: pytest.fail("should not probe"))
    assert run_discovery(domain.id, now)["probed"] == 0


# --- endpoints ---------------------------------------------------------------------------------------


def test_discovery_endpoints_are_admin_only(client, jwt_header, make_user, monkeypatch):
    import scanner.tasks as tasks_mod
    admin, owner = make_user("root", is_admin=True), make_user("owner")
    domain = _domain()
    now = datetime(2026, 11, 1)
    db.session.add(DiscoveredHost(domain_id=domain.id, host="lab.cs.example.edu", status="new", sources="ct",
                                  first_seen=now, last_seen=now, resolves=True, http_status=200))
    db.session.commit()
    queued = []
    monkeypatch.setattr(tasks_mod.discover_hosts, "delay", lambda domain_id: queued.append(domain_id) or types.SimpleNamespace(id="t-1"))

    assert client.post(f"/api/domains/{domain.id}/discover/", headers=jwt_header(owner)).status_code == 403
    resp = client.post(f"/api/domains/{domain.id}/discover/", headers=jwt_header(admin))
    assert resp.status_code == 202 and queued == [domain.id]

    assert client.get(f"/api/domains/{domain.id}/discovered/", headers=jwt_header(owner)).status_code == 403
    body = client.get(f"/api/domains/{domain.id}/discovered/", headers=jwt_header(admin)).get_json()
    assert [row["host"] for row in body["items"]] == ["lab.cs.example.edu"]
    host_id = body["items"][0]["id"]

    resp = client.patch(f"/api/domains/discovered/{host_id}/", json={"status": "ignored", "note": "Old lab"},
                        headers=jwt_header(admin))
    assert resp.get_json()["status"] == "ignored"
    assert client.patch(f"/api/domains/discovered/{host_id}/", json={"status": "tracked"},
                        headers=jwt_header(admin)).status_code == 400
    assert client.get(f"/api/domains/{domain.id}/discovered/?status=new", headers=jwt_header(admin)).get_json()["items"] == []

    resp = client.patch(f"/api/domains/{domain.id}/", json={"discovery_enabled": True}, headers=jwt_header(admin))
    assert resp.get_json()["discovery_enabled"] is True


def test_weekly_task_queues_enabled_domains_only(app, monkeypatch):
    import scanner.tasks as tasks_mod
    on, off = _domain("cs.example.edu"), _domain("math.example.edu")
    on.discovery_enabled = True
    db.session.commit()
    queued = []
    monkeypatch.setattr(tasks_mod.discover_hosts, "delay", lambda domain_id: queued.append(domain_id))
    assert tasks_mod.discover_all_domains.run() == {"queued": 1}
    assert queued == [on.id]


def test_deleting_a_domain_removes_discovered_hosts(app):
    domain = _domain()
    now = datetime(2026, 11, 1)
    db.session.add(DiscoveredHost(domain_id=domain.id, host="x.cs.example.edu", first_seen=now, last_seen=now))
    db.session.commit()
    domain.delete()
    assert db.session.query(DiscoveredHost).count() == 0

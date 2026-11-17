"""Departments: one spelling per department on save, the merge of existing variants
(and its CLI), the counts endpoint, business owners snapped to usernames, user search."""
import pytest

import models.website as website_models
from models import db
from services.departments import canonical_department, merge_departments, plan_department_merge, tidy


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setattr(website_models, "is_valid_url", lambda url: True)


def _sites(make_user, make_website, departments):
    owner = make_user("owner")
    sites = []
    for index, department in enumerate(departments):
        website = make_website(owner, base=f"https://s{index}.example")
        website.department = department
        sites.append(website)
    db.session.commit()
    return owner, sites


def test_tidy():
    assert tidy("  Computer   Science ") == "Computer Science"
    assert tidy("   ") is None and tidy(None) is None


def test_canonical_department_uses_existing_spelling(app, make_user, make_website):
    _sites(make_user, make_website, ["Computer Science", "Computer Science", "computer science", "Math"])
    assert canonical_department(" computer   SCIENCE ") == "Computer Science"  # most used spelling
    assert canonical_department("Physics  Dept") == "Physics Dept"  # new: tidied only
    assert canonical_department("") is None


def test_saving_snaps_department_and_business_owner(client, jwt_header, make_user, make_website):
    owner, (cs, other) = _sites(make_user, make_website, ["Computer Science", None])
    make_user("JDoe")
    resp = client.patch(f"/api/websites/{other.id}/", headers=jwt_header(owner),
                        json={"department": "computer science ", "business_owner": "  jdoe "})
    body = resp.get_json()
    assert body["department"] == "Computer Science"
    assert body["business_owner"] == "JDoe"
    # A NetID that is not a user yet is kept as typed (tidied).
    body = client.patch(f"/api/websites/{other.id}/", headers=jwt_header(owner),
                        json={"business_owner": " newperson "}).get_json()
    assert body["business_owner"] == "newperson"


def test_merge_plan_variants_and_mapping(app, make_user, make_website):
    _sites(make_user, make_website,
           ["Computer Science", "Computer Science", "computer science", "Computer  Science ", "CS", "Math", "math"])
    plan = plan_department_merge({"cs": "Computer Science"})
    assert plan == {
        "computer science": "Computer Science",
        "Computer  Science ": "Computer Science",
        "CS": "Computer Science",
        "math": "Math",  # tie (one each): alphabetical first, "Math" < "math"
    }
    result = merge_departments({"cs": "Computer Science"}, dry_run=True)
    assert result["websites"] == 4
    assert {w.department for w in db.session.query(website_models.Website).all()} >= {"CS", "math"}  # untouched

    result = merge_departments({"cs": "Computer Science"})
    assert result["websites"] == 4
    names = sorted(w.department for w in db.session.query(website_models.Website).all())
    assert names == ["Computer Science"] * 5 + ["Math"] * 2


def test_mapping_to_a_new_name(app, make_user, make_website):
    _sites(make_user, make_website, ["CS", "cs"])
    assert plan_department_merge({"CS": "Computer Science"}) == {"CS": "Computer Science", "cs": "Computer Science"}


def test_merge_cli(app, make_user, make_website):
    from commands import maintenance_cli
    _sites(make_user, make_website, ["Math", "math ", "CS"])
    runner = app.test_cli_runner()
    result = runner.invoke(maintenance_cli, ["merge-departments", "--dry-run", "--map", "CS=Computer Science"])
    assert result.exit_code == 0, result.output
    assert "'CS' -> 'Computer Science'" in result.output and "2 websites would change" in result.output
    result = runner.invoke(maintenance_cli, ["merge-departments", "--map", "nonsense"])
    assert result.exit_code != 0
    result = runner.invoke(maintenance_cli, ["merge-departments"])
    assert "1 websites changed" in result.output


def test_departments_endpoint_counts(client, jwt_header, make_user, make_website):
    owner, _ = _sites(make_user, make_website, ["CS", "CS", "Math"])
    headers = jwt_header(owner)
    assert client.get("/api/websites/departments/", headers=headers).get_json() == ["CS", "Math"]
    assert client.get("/api/websites/departments/?counts=true", headers=headers).get_json() == [
        {"name": "CS", "count": 2}, {"name": "Math", "count": 1}]


def test_user_search(client, jwt_header, make_user):
    me = make_user("alice")
    make_user("alan")
    make_user("bob")
    headers = jwt_header(me)
    assert client.get("/api/users/search/?q=AL", headers=headers).get_json() == ["alan", "alice"]
    assert client.get("/api/users/search/?q=%25", headers=headers).get_json() == []  # no wildcard injection
    assert len(client.get("/api/users/search/", headers=headers).get_json()) == 3
    assert client.get("/api/users/search/?q=a").status_code == 401

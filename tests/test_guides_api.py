"""Fix guides: the markdown files in guides/, served at /api/guides for anyone."""
import pytest

import services.guides as guides_mod
from services.guides import GUIDES_DIR, PLATFORMS, available_guides, parse_guide

SAMPLE = """---
title: Sample guide
impact: serious
summary: One line.
wcag: 1.1.1, 4.1.2
deque: https://dequeuniversity.com/rules/axe/4.10/sample
---

## What this means

Meaning.

## Before

```html
<div>## not a heading</div>
```

## Plain HTML

HTML steps.

## WordPress

WP steps.
"""


def test_index_lists_guides_anonymously(client):
    resp = client.get("/api/guides/")

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["count"] == len(available_guides()) >= 1
    titles = [item["title"] for item in body["items"]]
    assert titles == sorted(titles, key=str.lower)
    assert "region" in {item["rule_id"] for item in body["items"]}
    assert "public" in resp.headers["Cache-Control"]


def test_detail_splits_front_matter_sections_and_platforms(client, tmp_path, monkeypatch):
    (tmp_path / "sample.md").write_text(SAMPLE)
    monkeypatch.setattr(guides_mod, "GUIDES_DIR", tmp_path)

    resp = client.get("/api/guides/sample/")

    assert resp.status_code == 200
    guide = resp.get_json()
    assert (guide["title"], guide["impact"], guide["wcag"]) == ("Sample guide", "serious", ["1.1.1", "4.1.2"])
    assert [section["id"] for section in guide["sections"]] == ["what-this-means", "before"]
    assert "## not a heading" in guide["sections"][1]["markdown"]  # code blocks are not split
    assert [(p["id"], p["label"]) for p in guide["platforms"]] == [("wordpress", "WordPress"), ("html", "Plain HTML")]
    assert not guide["markdown"].startswith("---")
    assert client.get("/api/guides/").get_json()["items"] == [
        {"rule_id": "sample", "title": "Sample guide", "impact": "serious", "summary": "One line."}
    ]


def test_unknown_and_malformed_ids_are_404(client):
    for path in ("/api/guides/nope/", "/api/guides/Region/", "/api/guides/..%2Fapp/", "/api/guides/-bad/"):
        assert client.get(path).status_code == 404, path


@pytest.mark.parametrize("path", sorted(GUIDES_DIR.glob("*.md")), ids=lambda path: path.stem)
def test_every_shipped_guide_is_well_formed(path):
    guide = parse_guide(path.stem, path.read_text())

    assert guide["title"] and guide["summary"]
    assert guide["impact"] in ("critical", "serious", "moderate", "minor")
    assert [s["id"] for s in guide["sections"]] == ["what-this-means", "why-it-matters", "before", "after", "check-your-fix"]
    assert [p["id"] for p in guide["platforms"]] == [platform_id for platform_id, _ in PLATFORMS]
    assert all(p["markdown"] for p in guide["platforms"]) and all(s["markdown"] for s in guide["sections"])

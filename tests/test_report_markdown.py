"""Unit tests for the report Markdown / agent-prompt renderers."""
from utils.markdown import report_to_agent_prompt, report_to_markdown


def test_markdown_contains_metadata_counts_and_violation(
    app, make_user, make_site, add_report
):
    user = make_user()
    report = add_report(make_site(user))
    md = report_to_markdown(report)

    assert f"# Accessibility Report for {report.url}" in md
    # counts table header
    assert "| Category | Total | Critical | Serious | Moderate | Minor |" in md
    # violation details
    assert "color-contrast" in md
    assert "div.banner" in md
    assert "Fix the contrast" in md


def test_agent_prompt_matches_ui_shape(app, make_user, make_site, add_report):
    user = make_user()
    report = add_report(make_site(user))
    prompt = report_to_agent_prompt(report)

    assert prompt.startswith("# Accessibility Violations Report")
    assert "**Total Issues:** 1" in prompt
    assert "## 1. color-contrast [serious]" in prompt
    assert "Selector: `div.banner`" in prompt


def test_renderers_handle_no_violations(app, make_user, make_site, add_report):
    user = make_user()
    report = add_report(make_site(user), violations=[])

    md = report_to_markdown(report)
    assert "## Violations (0)" in md
    assert "_None found._" in md

    prompt = report_to_agent_prompt(report)
    assert "**Total Issues:** 0" in prompt

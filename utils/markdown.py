"""Markdown renderers for accessibility reports.

``report_to_markdown`` produces a human-readable Markdown document.
``report_to_agent_prompt`` mirrors the frontend "AI Fix Prompt"
(accessibility-front/src/components/GenerateAIPromptButton.tsx) so the API
output matches the in-app button.
"""
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from models.report import Report
    from models.website import Website

# Result categories rendered in the human-readable report, in priority order.
_SECTIONS = [
    ("violations", "Violations"),
    ("inaccessible", "Inaccessible Elements"),
    ("incomplete", "Incomplete Checks"),
]


def report_to_markdown(report: 'Report') -> str:
    lines: List[str] = []
    lines.append(f"# Accessibility Report for {report.url}")
    lines.append("")
    lines.append(f"- **Report ID:** {report.id}")
    lines.append(f"- **URL:** {report.url}")
    if report.base_url:
        lines.append(f"- **Base URL:** {report.base_url}")
    lines.append(f"- **Timestamp:** {report.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    if report.tags:
        lines.append(f"- **Tags:** {', '.join(report.tags)}")
    lines.append("")

    # Summary counts table
    lines.append("## Summary")
    lines.append("")
    lines.append("| Category | Total | Critical | Serious | Moderate | Minor |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for category, counts in report.report_counts.items():
        lines.append(
            f"| {category.capitalize()} | {counts['total']} | {counts['critical']} | "
            f"{counts['serious']} | {counts['moderate']} | {counts['minor']} |"
        )
    lines.append("")

    for key, heading in _SECTIONS:
        results = report.report.get(key, [])
        lines.append(f"## {heading} ({len(results)})")
        lines.append("")
        if not results:
            lines.append("_None found._")
            lines.append("")
            continue
        for result in results:
            lines.append(f"### {result.get('id', 'N/A')} [{result.get('impact', 'unknown')}]")
            lines.append(f"- **Description:** {result.get('description', 'N/A')}")
            lines.append(f"- **Help:** {result.get('help', 'N/A')}")
            lines.append(f"- **Reference:** {result.get('helpUrl', 'N/A')}")
            nodes = result.get('nodes', [])
            if nodes:
                lines.append(f"- **Affected elements ({len(nodes)}):**")
                for node in nodes:
                    target = ', '.join(node.get('target', []))
                    lines.append(f"  - Selector: `{target}`")
                    lines.append(f"    HTML: `{node.get('html', '')}`")
                    failure = node.get('failureSummary')
                    if failure:
                        lines.append(f"    Failure: {failure}")
            lines.append("")

    return "\n".join(lines)


def website_report_to_markdown(website: 'Website') -> str:
    """Readable Markdown for a website's aggregated report (all pages combined)."""
    report = website.get_report()
    counts = website.get_report_counts()
    lines: List[str] = []
    lines.append(f"# Accessibility Report for {website.url}")
    lines.append("")
    lines.append(f"- **Website:** {website.url}")
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append("| Category | Total | Critical | Serious | Moderate | Minor |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for category, c in (counts or {}).items():
        lines.append(
            f"| {category.capitalize()} | {c['total']} | {c['critical']} | "
            f"{c['serious']} | {c['moderate']} | {c['minor']} |"
        )
    lines.append("")

    violations = report.get('violations', [])
    lines.append(f"## Violations ({len(violations)})")
    lines.append("")
    if not violations:
        lines.append("_None found._")
        lines.append("")
    else:
        for v in violations:
            lines.append(f"### {v.get('id', 'N/A')} [{v.get('impact', 'unknown')}]")
            lines.append(f"- **Description:** {v.get('description', 'N/A')}")
            lines.append(f"- **Help:** {v.get('help', 'N/A')}")
            lines.append(f"- **Reference:** {v.get('helpUrl', 'N/A')}")
            pages = v.get('reports', [])
            if pages:
                lines.append(f"- **Affected pages ({len(pages)}):**")
                for p in pages:
                    lines.append(f"  - {p.get('url')}")
            lines.append("")

    return "\n".join(lines)


def website_report_to_agent_prompt(website: 'Website') -> str:
    """AI fix-prompt for a website's aggregated violations across all pages.

    Mirrors GenerateAIPromptButton.buildPrompt for website-level results.
    """
    report = website.get_report()
    violations = report.get('violations', [])
    lines: List[str] = []

    lines.append("# Accessibility Violations Report")
    lines.append(f"**URL:** {website.url}")
    lines.append(f"**Total Issues:** {len(violations)}")
    lines.append("")
    lines.append(
        "Please fix the following accessibility violations. Each issue includes the "
        "rule ID, severity, description, and the affected HTML elements or pages."
    )
    lines.append("")

    for i, v in enumerate(violations):
        lines.append(f"## {i + 1}. {v.get('id', 'N/A')} [{v.get('impact') or 'unknown'}]")
        lines.append(f"- **Description:** {v.get('description', '')}")
        lines.append(f"- **Help:** {v.get('help', '')}")
        lines.append(f"- **Reference:** {v.get('helpUrl', '')}")

        pages = v.get('reports', [])
        if pages:
            lines.append(f"- **Affected pages ({len(pages)}):**")
            for p in pages:
                lines.append(f"  - {p.get('url')}")

        nodes = v.get('nodes', [])
        if nodes:
            lines.append(f"- **Affected elements ({len(nodes)}):**")
            for node in nodes:
                target = ', '.join(node.get('target', []))
                lines.append(f"  - Selector: `{target}`")
                lines.append(f"    HTML: `{node.get('html', '')}`")
                failure = node.get('failureSummary')
                if failure:
                    lines.append(f"    Failure: {failure}")

        lines.append("")

    return "\n".join(lines)


def report_to_agent_prompt(report: 'Report') -> str:
    """Port of GenerateAIPromptButton.buildPrompt for a single report."""
    violations = report.report.get('violations', [])
    lines: List[str] = []

    lines.append("# Accessibility Violations Report")
    lines.append(f"**URL:** {report.url}")
    lines.append(f"**Total Issues:** {len(violations)}")
    lines.append("")
    lines.append(
        "Please fix the following accessibility violations. Each issue includes the "
        "rule ID, severity, description, and the affected HTML elements or pages."
    )
    lines.append("")

    for i, v in enumerate(violations):
        lines.append(f"## {i + 1}. {v.get('id', 'N/A')} [{v.get('impact') or 'unknown'}]")
        lines.append(f"- **Description:** {v.get('description', '')}")
        lines.append(f"- **Help:** {v.get('help', '')}")
        lines.append(f"- **Reference:** {v.get('helpUrl', '')}")

        nodes = v.get('nodes', [])
        if nodes:
            lines.append(f"- **Affected elements ({len(nodes)}):**")
            for node in nodes:
                target = ', '.join(node.get('target', []))
                lines.append(f"  - Selector: `{target}`")
                lines.append(f"    HTML: `{node.get('html', '')}`")
                failure = node.get('failureSummary')
                if failure:
                    lines.append(f"    Failure: {failure}")

        lines.append("")

    return "\n".join(lines)

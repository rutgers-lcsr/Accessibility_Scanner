from pathlib import Path
from playwright.async_api import Page
from typing import TypedDict, List, Literal, Optional

from scanner.log import log_message

# axe-core is vendored next to this module so scans need no network access to a CDN.
# Upgrade by replacing the file (see the version banner on its first line).
AXE_PATH = Path(__file__).with_name("axe.min.js")

class AxeCheck(TypedDict, total=False):
    id: str
    impact: Optional[Literal["minor", "moderate", "serious", "critical"]]
    message: str
    data: dict
    relatedNodes: List[dict]


class AxeNode(TypedDict, total=False):
    html: str
    target: List[str]
    failureSummary: Optional[str]
    any: List[AxeCheck]
    all: List[AxeCheck]
    none: List[AxeCheck]


class AxeResult(TypedDict, total=False):
    id: str
    impact: Optional[Literal["minor", "moderate", "serious", "critical"]]
    description: str
    help: str
    helpUrl: str
    tags: List[str]
    nodes: List[AxeNode]


class AxeSiteReport(TypedDict):
    url:str
    timestamp: str
    report_id: int

class WebsiteAxeResult(AxeResult):
    reports: List[AxeSiteReport]

# https://www.deque.com/axe/core-documentation/api-documentation/#results-object
class AxeReport(TypedDict, total=False):
    url: str
    timestamp: str
    testEngine: str
    testEnvironment: str
    
    violations: List[AxeResult]
    passes: List[AxeResult]
    incomplete: List[AxeResult]
    inapplicable: List[AxeResult]
    
    
class WebsiteAxeReport(TypedDict):
    url:str
    violations: List[WebsiteAxeResult]
    passes: List[WebsiteAxeResult]
    incomplete: List[WebsiteAxeResult]
    inapplicable: List[WebsiteAxeResult]

AxeReportKeys = Literal["violations", "passes", "incomplete", "inapplicable"]


class AxeResultSummary(TypedDict, total=False):
    """A rule without its nodes: how passes and inapplicable results are stored."""
    id: str
    impact: Optional[Literal["minor", "moderate", "serious", "critical"]]
    description: str
    help: str
    helpUrl: str
    tags: List[str]
    node_count: int


_SUMMARISED_KEYS = ("passes", "inapplicable")
_SUMMARY_FIELDS = ("id", "impact", "description", "help", "helpUrl", "tags")


def _summarise(rule: dict) -> AxeResultSummary:
    summary = {key: rule[key] for key in _SUMMARY_FIELDS if key in rule}
    summary["node_count"] = rule.get("node_count", len(rule.get("nodes") or []))
    return summary


def slim_axe_report(report: AxeReport) -> AxeReport:
    """Drop the node lists of passing and inapplicable rules, keeping a node count.

    Those two lists are most of an axe result (a typical page carries the HTML of
    150+ passing nodes) and nobody acts on them; violations and incomplete keep their
    nodes. Idempotent, so it is safe to run over reports that are already slim.
    """
    slim = dict(report or {})
    for key in _SUMMARISED_KEYS:
        rules = slim.get(key)
        if rules:
            slim[key] = [_summarise(rule) for rule in rules]
    return slim




def get_axe_config(axe_config:str) -> str:
    if axe_config:
        return f"""async () => {{
            if (typeof axe.configure === 'function') {{
                axe.configure({axe_config});
                return true;
            }} else {{
                throw new Error('axe.configure is not a function' + JSON.stringify(axe, null, 4));
            }}
        }}"""
    return ""

def get_axe_js(tags: List[str]) -> str:
    tags_str = ', '.join([f"'{tag.strip()}'" for tag in tags])
    return f"""async () => {{
            const report = await axe.run({{
                runOnly: {{
                    type: 'tag',
                    values: [{tags_str}]
                }}
            }});
            
            report.testEngine = 'LCSRAccessibility';
            // convert errors to strings
            function cleanErrors(obj) {{
                if (obj && typeof obj === 'object') {{
                    if (Array.isArray(obj)) {{
                        return obj.map(cleanErrors);
                    }} else {{
                        const newObj = {{}};
                        for (const [key, value] of Object.entries(obj)) {{
                            if (value instanceof Error) {{
                                newObj[key] = value.toString();
                            }} else {{
                                newObj[key] = cleanErrors(value);
                            }}
                        }}
                        return newObj;
                    }}
                }}
                return obj;
            }}
            return cleanErrors(report);
            
        }}"""
async def get_accessibility_report(page: Page, tags:List[str] = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'], axe_config: str = "") -> AxeReport:
    
    try:
        await page.add_script_tag(path=str(AXE_PATH))
        await page.wait_for_function("window.axe !== undefined")
        if axe_config:
            await page.evaluate(get_axe_config(axe_config))

        result: AxeReport = await page.evaluate(get_axe_js(tags))
        return result
    except Exception as e:
        log_message(f"Error injecting or running axe-core: {e}", 'error')
        return {"error": str(e)}



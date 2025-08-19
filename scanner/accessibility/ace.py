from playwright.async_api import Page
from typing import TypedDict, List, Literal, Optional


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


class AxeReport(TypedDict, total=False):
    violations: List[AxeResult]
    passes: List[AxeResult]
    incomplete: List[AxeResult]
    inapplicable: List[AxeResult]


_ace_js = """async () => {
            return await axe.run({
                runOnly: {
                    type: 'tag',
                    values: ['wcag2a', 'wcag2aa','wcag21a', 'wcag21aa']
                }
            });
        }"""


async def get_accessibility_report(page: Page) -> AxeReport:
    await page.add_script_tag(url="https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.9.1/axe.min.js")
    result = await page.evaluate(_ace_js)
    return result



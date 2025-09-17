from requests import request
from playwright.async_api import Page
from typing import TypedDict, List, Literal, Optional

from scanner.log import log_message
from config import CLIENT_URL

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

AxeReportKeys = Literal["violations", "passes", "incomplete", "inapplicable"]




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
    
    axe_min_js_url = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.9.1/axe.min.js"
    try:
        try:
            await page.add_script_tag(url=axe_min_js_url)
        except Exception as e:
            log_message(f"Error adding axe script tag loading from file: {e}", 'error')
            # Fallback to loading from CDN manually
            res = request(method="GET", url=axe_min_js_url)
            content = res.text
            await page.add_script_tag(content=content)
            log_message(f"Loaded axe from manual CDN fallback", 'info')

        await page.wait_for_function("window.axe !== undefined")
        if axe_config:
            await page.evaluate(get_axe_config(axe_config))

        result: AxeReport = await page.evaluate(get_axe_js(tags))
        return result
    except Exception as e:
        log_message(f"Error injecting or running axe-core: {e}", 'error')
        return {"error": str(e)}



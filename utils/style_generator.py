

from hashlib import md5
import random
import string
from typing import List, Literal, TypedDict

from flask import json
from scanner.accessibility.ace import AxeResult
from scanner.log import log_message

LEVEL = {
    'critical': 'border: 4px solid darkred; z-index: 9990; position: relative;',
    'serious': 'border: 4px solid red; z-index: 9990; position: relative;',
    'moderate': 'border: 4px solid orange; z-index: 9990; position: relative;',
    'minor': 'border: 4px solid yellow; z-index: 9990; position: relative;',
    'null': 'border: 4px solid gray; z-index: 9990; position: relative;'
}

tooltip_style = "position: absolute; z-index: 9999;pointer-events: none; text-align: center; background-color: rgba(255, 255, 255, 0.9); text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2); color: black; padding: 5px; border-radius: 4px; font-size: 12px; font-family: Arial, sans-serif; top: 0; left: 0; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1); min-width: 300px; overflow: 'auto'; font-weight: bold; cursor: pointer; font-size: 14px;"

class Injection():
    selector: str
    style: str
    impact: Literal['critical', 'serious', 'moderate', 'minor', 'null']
    description: str
    message: str
    helping: str
    help_url: str
    html: str
    failure_summary: str


    def sanitize_js_string(s: str) -> str:
        return s.replace("`", "\\`").replace("\n", " ").replace("<", "&lt;").replace(">", "&gt;")

    def __init__(self, selector: str, style: str, impact: Literal['critical', 'serious', 'moderate', 'minor', 'null'], description: str, message: str, help: str, help_url: str, html: str, failure_summary: str):
        self.selector = selector
        self.style = style
        self.impact = impact
        
        # escape quotes and new lines and html in description, message, help, help_url
        self.description = self.sanitize_js_string(description)
        self.message = self.sanitize_js_string(message)
        self.help = self.sanitize_js_string(help)
        self.help_url = help_url
        self.html = self.sanitize_js_string(html) if html else ""
        self.failure_summary = self.sanitize_js_string(failure_summary) if failure_summary else ""

    def to_json(self):
        return {
            'selector': self.selector,
            'style': self.style,
            'impact': self.impact,
            'description': self.description,
            'message': self.message,
            'help': self.help,
            'help_url': self.help_url,
            'html': self.html or "",
            'failure_summary': self.failure_summary or "",
        }
    
    
        
def get_injections(report: List[AxeResult]) -> List[Injection]:
    injections = []
    try:
        for violation in report:
            if violation['impact'] not in LEVEL:
                log_message(f"Unknown impact level '{violation['impact']}' found. Defaulting to 'minor'.", 'warning')
                violation['impact'] = 'minor'
            if violation['description'] is None:
                violation['description'] = "No description provided."
            if violation['help'] is None:
                violation['help'] = "No help provided."
            if violation['helpUrl'] is None:
                violation['helpUrl'] = "No help URL provided."
            
            for node in violation['nodes']:
                    selector = ", ".join(node['target'])
                    injection =  Injection(
                        selector=selector,
                        style=LEVEL[violation.get('impact', 'minor')],
                        impact=violation.get('impact', 'minor'),
                        description=violation.get('description', ""),
                        message=violation.get('message', ""),
                        help=violation.get('help', ""),
                        help_url=violation.get('helpUrl', ""),
                        html=node.get('html', ""),
                        failure_summary=node.get('failureSummary', "")
                    )
                    
                    
                    injections.append(injection)
        return injections    
    except Exception as e:
        log_message(f"Error processing report: {e}", 'error')
        return []
    

def report_to_js(report: List[AxeResult], report_url: str, report_mode:bool = False) -> str:
    """Generates javascript which can be used to find accessibility violations in a webpage.

    Args:
        report (List[AxeResult]): The accessibility report containing violation details.
        report_url (str): The URL of the report to be included in the generated JavaScript.
        report_mode (bool): If True, disables user messages in the generated script.

    Returns:
        str: A string containing the generated JavaScript code.
    """
    # injections = []
    try:
        # for violation in report:
        #     if violation['impact'] not in LEVEL:
        #         log_message(f"Unknown impact level '{violation['impact']}' found. Defaulting to 'minor'.", 'warning')
        #         violation['impact'] = 'minor'
        #     if violation['description'] is None:
        #         violation['description'] = "No description provided."
        #     if violation['help'] is None:
        #         violation['help'] = "No help provided."
        #     if violation['helpUrl'] is None:
        #         violation['helpUrl'] = "No help URL provided."
            
        #     for node in violation['nodes']:
        #             selector = ", ".join(node['target'])
        #             injection =  Injection(
        #                 selector=selector,
        #                 style=LEVEL[violation.get('impact', 'minor')],
        #                 impact=violation.get('impact', 'minor'),
        #                 description=violation.get('description', ""),
        #                 message=violation.get('message', ""),
        #                 help=violation.get('help', ""),
        #                 help_url=violation.get('helpUrl', ""),
        #                 html=node.get('html', ""),
        #                 failure_summary=node.get('failureSummary', "")
        #             )
                    
                    
        #             injections.append(injection)

        injections = get_injections(report)
        js_code= generate_js_list(injections, report_url)
        
        
        if report_mode:
            # Disable user messages in Report mode
            js_code = js_code.replace("let showUserMessages = true;", "let showUserMessages = false;")
            
        return js_code    
    except Exception as e:
        log_message(f"Error processing report for JS generation: {e}", 'error')
        return ""


def generate_random_string(length):
    """
    Generates a random string of a specified length using uppercase letters and digits.

    Args:
        length (int): The desired length of the random string.

    Returns:
        str: The generated random string.
    """
    characters = string.ascii_uppercase + string.ascii_lowercase
    random_string = ''.join(random.choice(characters) for _ in range(length))
    return random_string

def generate_js(injection: Injection) -> str:
    selector_hash = generate_random_string(10)
    selector_small_hash = generate_random_string(5)
    selector_toolTip_hash = generate_random_string(5)
    js_code = f"""
try {{
    
    
    var {selector_small_hash} = document.querySelector(`{str(injection['selector'])}`);
    var {selector_toolTip_hash} = null;
    if (!{selector_small_hash}) {{
        accesslog(`Selector not found: {injection['selector']}`, "warning");
        throw new Error('Selector not found');
    }}
    
    
    if (injections.has(`{injection['selector']}`)) {{
        {selector_toolTip_hash} = injections.get(`{injection['selector']}`);
    }} else {{
        {selector_toolTip_hash} = document.createElement('div');
    }}
    
    
    
    
    var {selector_small_hash}_old_style = {selector_small_hash}.getAttribute('style') || "";
    {selector_small_hash}.style = "{injection['style']}" + {selector_small_hash}_old_style;
    {selector_small_hash}.setAttribute('data-violation-description', `{injection['description']}`);
    {selector_small_hash}.setAttribute('data-violation-message', `{injection['message']}`);
    {selector_small_hash}.setAttribute('data-violation-help', `{injection['help']}`);
    {selector_small_hash}.setAttribute('data-violation-help-url', `{injection['help_url']}`);
    {selector_small_hash}.onmouseenter = function() {{
        accesslog(`Tooltip shown for:{injection['message']}\n{injection['description']}\n{injection['help']}\nLearn More at: {injection['help_url']}`);

        var tooltip = document.createElement('div');
        tooltip.className = 'tooltip-{selector_hash}';
        tooltip.innerHTML = `[{injection['impact']}] {injection['message']} <br> {injection['help']} <br> Click to Learn More`;
        tooltip.style = "{tooltip_style}";
        {selector_small_hash}.appendChild(tooltip);
    }};
    {selector_small_hash}.onmouseleave = function() {{
        var tooltip = document.querySelector('.tooltip-{selector_hash}');
        if (tooltip) {{
            {selector_small_hash}.removeChild(tooltip);
        }}
    }};
    
    {selector_small_hash}.onclick = function() {{
        window.open(`{injection['help_url']}`, '_blank');
    }};
    accesslog(`Marked: {injection['selector']} with hash {selector_hash}`);
    console.log({selector_small_hash});
}}
catch (error) {{
    accesslog('Error injecting styles:',"error", error);
}}
    """
    return js_code


def generate_js_list(injections: List[Injection], report_url: str) -> str:
    """Generates JavaScript code to apply the given styles to a webpage.

    Args:
        styles (List[dict]): A list of style objects containing selector and properties.

    Returns:
        str: A string containing the generated JavaScript code.
    """
    
    injections_json = [inj.to_json() for inj in injections]

    injections_json_str = json.dumps(injections_json).replace("`", "\\`").replace("\\n", " ")


    with open("utils/styles.js", "r") as f:
        base_js = f.read()
    base_js = base_js.replace("var injections = [];", f"""var injections = {injections_json_str}""")

    js_code = f"""
/* 
This script was generated by the Accessibility Scanner
*/
var header = `****** Accessibility Scanner Report Script ******`
console.log(header)

const currentUrl = window.location.href;
var accesslog = (message, level = "info", ...args) => {{
    console.log(`[Access] [${{level}}]: ${{message}}`, ...args);
}};
if(currentUrl.includes(`{report_url}`)) {{
  
    {base_js}

}} else {{
    accesslog(`The report URL does not match the current URL. Report URL: {report_url}, Current URL: ${{currentUrl}}`, "warning");
    accesslog(`This error occurs because the script was run outside the report context.`, "warning");
    accesslog(`You might have pasted the script into the wrong element on the Report page or ran it on the wrong page.`, "warning");
    accesslog(`Please ensure you are running the script in the correct context.`, "warning");
    accesslog(`If you still have issues please check out this https://developer.chrome.com/docs/devtools/console/reference#context to help with switching contexts.`, "warning");
    
}}
"""



    return js_code
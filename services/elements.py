"""Every current failing element of a website, grouped by the markup it shares.

A page full of failures is usually one template or one stylesheet repeated: 36 code
tokens in one highlight colour, a dozen buttons from one component. Grouping by the
element's tag and classes (positions dropped) and, for contrast, its colour pair puts the
one fix in front of the developer instead of 36 rows.
"""
import re

from services.findings import list_findings

_TAG = re.compile(r'<\s*([a-zA-Z][a-zA-Z0-9-]*)([^>]*)>?')
_CLASS = re.compile(r'\bclass\s*=\s*["\']([^"\']*)["\']')
_COLOURS = re.compile(r'foreground color: (#[0-9a-fA-F]{3,8}), background color: (#[0-9a-fA-F]{3,8})')


def signature(rule_id: str, html: str | None, failure_summary: str | None) -> dict:
    """``{'key', 'label'}`` shared by elements a single fix is likely to clear."""
    label = '(no markup)'
    match = _TAG.search(html or '')
    if match:
        tag = match.group(1).lower()
        classes = _CLASS.search(match.group(2) or '')
        # Generated CSS-in-JS classes (css-1x2y3z, css-var-…) differ between builds of
        # the same component; they would split one group into many.
        names = sorted({c for c in classes.group(1).split() if not c.startswith('css-')}) if classes else []
        label = f'<{tag} class="{" ".join(names)}">' if names else f'<{tag}>'
    colours = _COLOURS.search(failure_summary or '')
    if colours:
        label += f' · {colours.group(1).lower()} on {colours.group(2).lower()}'
    return {'key': f'{rule_id}\n{label}', 'label': label}


def website_elements(site_ids, rule_id: str | None = None) -> dict:
    """The current findings of the given pages as groups of shared markup, largest first.
    Each element carries its page, report, selector, HTML, failure text and status."""
    listing = list_findings(site_ids, 'current', rule_id)
    groups = {}
    for rule in listing['rules']:
        for page in rule['pages']:
            for finding in page['findings']:
                sig = signature(rule['rule_id'], finding.get('html'), finding.get('failure_summary'))
                group = groups.setdefault(sig['key'], {
                    'key': sig['key'], 'label': sig['label'], 'rule_id': rule['rule_id'],
                    'impact': rule['impact'], 'help': rule['help'], 'elements': [], 'urls': set(),
                })
                group['urls'].add(page['url'])
                group['elements'].append({
                    'id': finding['id'], 'url': page['url'], 'report_id': page['report_id'],
                    'selector': finding.get('selector'), 'html': finding.get('html'),
                    'failure_summary': finding.get('failure_summary'),
                    'status': finding.get('status'), 'note': finding.get('note'),
                    'status_by': finding.get('status_by'), 'status_at': finding.get('status_at'),
                })
    ordered = sorted(groups.values(), key=lambda g: (-len(g['elements']), g['label']))
    for group in ordered:
        group['count'] = len(group['elements'])
        group['pages'] = len(group.pop('urls'))
    return {'count': listing['count'], 'groups': ordered}


CSV_COLUMNS = ['id', 'rule', 'impact', 'group', 'page', 'selector', 'html', 'failure', 'status', 'note',
               'status_by', 'status_at', 'report']


def csv_rows(data: dict, base_url: str = ''):
    for group in data['groups']:
        for element in group['elements']:
            yield [
                element['id'], group['rule_id'], group['impact'], group['label'], element['url'], element['selector'],
                element['html'], element['failure_summary'], element['status'], element['note'],
                element['status_by'], element['status_at'],
                f"{base_url}/reports/{element['report_id']}" if element['report_id'] else None,
            ]

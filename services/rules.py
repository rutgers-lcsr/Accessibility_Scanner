"""Custom axe rules through the API: turn a request body into a Rule with its checks,
reporting every problem at once, and serialize rules back in that same shape."""
import json

from models import db
from models.rules import Check, Rule
from models.settings import Settings
from models.website import Website

IMPACTS = ('minor', 'moderate', 'serious', 'critical')
CHECK_GROUPS = ('any', 'all', 'none')
MAX_LENGTH = 255  # Rule.name, Rule.selector, Rule.help_url and Check.name columns

RULE_FIELDS = {
    'name', 'description', 'help', 'help_url', 'impact', 'tags', 'selector', 'matches',
    'exclude_hidden', 'enabled', *CHECK_GROUPS,
}
CHECK_FIELDS = {'name', 'evaluate', 'options', 'pass_text', 'fail_text', 'incomplete_text'}
# Serialized rules carry these; they are ignored on input so a fetched rule can be sent back.
READ_ONLY_FIELDS = {'id', 'created_at', 'updated_at', 'websites_running'}


class RuleInputError(ValueError):
    """Every problem found in a rule body, each as {'field': path, 'message': text}."""

    def __init__(self, errors: list[dict]):
        super().__init__('; '.join(f"{e['field']}: {e['message']}" for e in errors))
        self.errors = errors


def _error(field: str, message: str) -> dict:
    return {'field': field, 'message': message}


def _unknown_fields(data: dict, allowed: set, prefix: str, errors: list):
    for key in sorted(set(data) - allowed - READ_ONLY_FIELDS):
        errors.append(_error(f'{prefix}{key}', f"unknown field; allowed fields are {', '.join(sorted(allowed))}"))


def _text(data: dict, key: str, path: str, errors: list, required=True, max_length=None) -> str | None:
    value = data.get(key)
    if value is None or (isinstance(value, str) and not value.strip()):
        if required:
            errors.append(_error(path, 'is required'))
        return None
    if not isinstance(value, str):
        errors.append(_error(path, 'must be a string'))
        return None
    value = value.strip()
    if max_length and len(value) > max_length:
        errors.append(_error(path, f'must be at most {max_length} characters'))
        return None
    return value


def _bool(data: dict, key: str, default: bool, errors: list) -> bool:
    value = data.get(key, default)
    if not isinstance(value, bool):
        errors.append(_error(key, 'must be true or false'))
        return default
    return value


def _tags(value, errors: list) -> list[str]:
    if not isinstance(value, list) or not value:
        errors.append(_error('tags', 'must be a non-empty list of strings'))
        return []
    tags = []
    for i, tag in enumerate(value):
        if not isinstance(tag, str) or not tag.strip():
            errors.append(_error(f'tags[{i}]', 'must be a non-empty string'))
        elif ',' in tag:
            errors.append(_error(f'tags[{i}]', 'must not contain a comma'))
        else:
            tags.append(tag.strip())
    return tags


def _parse_check(data, path: str, errors: list, seen_names: set) -> Check | None:
    if not isinstance(data, dict):
        errors.append(_error(path, 'must be an object'))
        return None
    before = len(errors)
    _unknown_fields(data, CHECK_FIELDS, f'{path}.', errors)
    name = _text(data, 'name', f'{path}.name', errors, max_length=MAX_LENGTH)
    evaluate = _text(data, 'evaluate', f'{path}.evaluate', errors)
    pass_text = _text(data, 'pass_text', f'{path}.pass_text', errors)
    fail_text = _text(data, 'fail_text', f'{path}.fail_text', errors)
    incomplete_text = _text(data, 'incomplete_text', f'{path}.incomplete_text', errors, required=False)
    options = data.get('options')
    if options is not None and not isinstance(options, dict):
        errors.append(_error(f'{path}.options', 'must be an object'))
    if name:
        if name in seen_names:
            errors.append(_error(f'{path}.name', 'is used by another check in this rule'))
        elif db.session.query(Check.id).filter_by(name=name).first():
            errors.append(_error(f'{path}.name', 'a check with this name already exists'))
        seen_names.add(name)
    if len(errors) > before:
        return None

    check = Check(
        name=name,
        evaluate=evaluate,
        options=json.dumps(options) if options is not None else None,
        pass_text=pass_text,
        fail_text=fail_text,
        incomplete_text=incomplete_text or '',
    )
    try:
        check.validate()
    except ValueError as e:
        errors.append(_error(path, str(e)))
        return None
    return check


def build_rule(data) -> Rule:
    """A validated, unsaved Rule with its new checks built from a request body.

    Raises RuleInputError listing every problem found. Nothing is added to the session.
    """
    if not isinstance(data, dict):
        raise RuleInputError([_error('body', 'must be a JSON object')])

    errors = []
    _unknown_fields(data, RULE_FIELDS, '', errors)
    name = _text(data, 'name', 'name', errors, max_length=MAX_LENGTH)
    if name and db.session.query(Rule.id).filter_by(name=name).first():
        errors.append(_error('name', 'a rule with this name already exists'))
    description = _text(data, 'description', 'description', errors)
    help_text = _text(data, 'help', 'help', errors)
    help_url = _text(data, 'help_url', 'help_url', errors, required=False, max_length=MAX_LENGTH)
    impact = data.get('impact')
    if impact not in IMPACTS:
        errors.append(_error('impact', f"must be one of: {', '.join(IMPACTS)}"))
    tags = _tags(data.get('tags'), errors)
    selector = _text(data, 'selector', 'selector', errors, required=False, max_length=MAX_LENGTH) or '*'
    matches = _text(data, 'matches', 'matches', errors, required=False)
    exclude_hidden = _bool(data, 'exclude_hidden', True, errors)
    enabled = _bool(data, 'enabled', True, errors)
    rule_fields_ok = not errors

    seen_names = set()
    groups = {}
    for group in CHECK_GROUPS:
        entries = data.get(group) or []
        if not isinstance(entries, list):
            errors.append(_error(group, 'must be a list of checks'))
            entries = []
        groups[group] = [_parse_check(entry, f'{group}[{i}]', errors, seen_names) for i, entry in enumerate(entries)]
    if not any(groups.values()):
        errors.append(_error('any', 'the rule needs at least one check in any, all or none'))

    rule = None
    if rule_fields_ok:
        rule = Rule(
            name=name,
            selector=selector,
            exclude_hidden=exclude_hidden,
            enabled=enabled,
            matches=matches,
            description=description,
            help=help_text,
            help_url=help_url,
            tags=tags,
            impact=impact,
        )
        rule.any = [check for check in groups['any'] if check]
        rule.all = [check for check in groups['all'] if check]
        rule.none = [check for check in groups['none'] if check]
        try:
            rule.validate()
        except ValueError as e:
            errors.append(_error('rule', str(e)))

    if errors:
        raise RuleInputError(errors)
    return rule


def active_website_tags() -> list[set[str]]:
    """The scan tags of every active website, as Website.get_tags computes them: the
    website's own tags plus the default tags."""
    defaults = {tag.strip() for tag in (Settings.get('default_tags') or '').split(',') if tag.strip()}
    rows = db.session.query(Website.tags).filter(Website.active.is_(True)).all()
    return [defaults | {tag.strip() for tag in (tags or '').split(',') if tag.strip()} for (tags,) in rows]


def _iso(when) -> str | None:
    return when.strftime('%Y-%m-%dT%H:%M:%SZ') if when else None


def serialize_check(check: Check) -> dict:
    return {
        'name': check.name,
        'evaluate': check.evaluate,
        'options': json.loads(check.options) if check.options else None,
        'pass_text': check.pass_text,
        'fail_text': check.fail_text,
        'incomplete_text': check.incomplete_text,
    }


def serialize_rule(rule: Rule, website_tags: list[set[str]]) -> dict:
    """The rule in the shape build_rule accepts, plus its id, timestamps and how many
    active websites run it (a scan runs a rule when one of the rule's tags is among the
    website's scan tags). ``website_tags`` is from active_website_tags()."""
    tags = [tag for tag in rule.tags.split(',') if tag]
    running = sum(1 for scan_tags in website_tags if scan_tags.intersection(tags)) if rule.enabled else 0
    return {
        'id': rule.id,
        'name': rule.name,
        'description': rule.description,
        'help': rule.help,
        'help_url': rule.help_url,
        'impact': rule.impact,
        'tags': tags,
        'selector': rule.selector,
        'matches': rule.matches,
        'exclude_hidden': rule.exclude_hidden,
        'enabled': rule.enabled,
        'any': [serialize_check(check) for check in rule.any],
        'all': [serialize_check(check) for check in rule.all],
        'none': [serialize_check(check) for check in rule.none],
        'websites_running': running,
        'created_at': _iso(rule.created_at),
        'updated_at': _iso(rule.updated_at),
    }

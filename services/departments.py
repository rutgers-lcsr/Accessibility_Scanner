"""Department names on websites: one spelling per department.

Department is free text on the website, so "Computer Science", "computer  science" and
"CS" would be three departments in the scorecards. canonical_department snaps a new value
to an existing spelling when they differ only in case or spacing; merge_departments
cleans up existing rows (case and spacing variants automatically, abbreviations through
an explicit mapping).
"""
from collections import Counter, defaultdict

from sqlalchemy import func

from models import db
from models.website import Website


def tidy(value: str | None) -> str | None:
    """Trimmed, inner whitespace collapsed; None for nothing."""
    if value is None:
        return None
    value = ' '.join(str(value).split())
    return value or None


def _key(value: str) -> str:
    return ' '.join(value.split()).casefold()


def department_counts(query=None) -> list:
    """``[{'name', 'count'}]`` for the departments on the websites ``query`` selects
    (every website by default), most used first."""
    query = query if query is not None else db.session.query(Website)
    rows = (query.with_entities(Website.department, func.count(Website.id))
            .filter(Website.department.isnot(None), Website.department != '')
            .group_by(Website.department).all())
    return sorted(({'name': name, 'count': count} for name, count in rows), key=lambda r: (-r['count'], r['name']))


def canonical_department(value: str | None) -> str | None:
    """``value`` tidied, spelled like an existing department that differs only in case
    or spacing (the most used spelling when there are several)."""
    value = tidy(value)
    if value is None:
        return None
    key = _key(value)
    matches = [row for row in department_counts() if _key(row['name']) == key]
    return matches[0]['name'] if matches else value


def plan_department_merge(mapping: dict | None = None) -> dict:
    """``{old spelling: new spelling}`` for every website department that should change:
    spacing and case variants go to the most used spelling (ties: the alphabetically
    first), and ``mapping`` (``{variant: target}``, matched ignoring case and spacing)
    renames abbreviations and the like."""
    # {variant key: target text}
    renames = {_key(old): tidy(new) for old, new in (mapping or {}).items() if tidy(old) and tidy(new)}
    usage = Counter({row['name']: row['count'] for row in department_counts()})

    # Group every spelling under the key of the department it should end up as.
    groups = defaultdict(list)
    for name in usage:
        groups[_key(renames.get(_key(name), name))].append(name)
    targets = {_key(new): new for new in renames.values()}

    plan = {}
    for key, names in groups.items():
        by_use = sorted(names, key=lambda n: (-usage[n], n))
        # An existing spelling of the department wins (most used first); otherwise the
        # mapping's spelling. tidy() drops stray spaces every variant may share.
        existing = [n for n in by_use if _key(n) == key]
        target = tidy(existing[0]) if existing else targets.get(key, tidy(by_use[0]))
        for name in names:
            if name != target:
                plan[name] = target
    return plan


def merge_departments(mapping: dict | None = None, dry_run: bool = False) -> dict:
    """Apply plan_department_merge. Returns ``{'plan', 'websites'}`` (websites changed,
    or that would change on a dry run)."""
    plan = plan_department_merge(mapping)
    changed = 0
    for old, new in plan.items():
        query = db.session.query(Website).filter(Website.department == old)
        if dry_run:
            changed += query.count()
        else:
            changed += query.update({Website.department: new}, synchronize_session=False)
    if not dry_run:
        db.session.commit()
    return {'plan': plan, 'websites': changed}

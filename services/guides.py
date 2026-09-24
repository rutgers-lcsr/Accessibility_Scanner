"""Fix guides: our own "how to fix" text per axe rule, kept as markdown files in guides/.

A guide starts with a front matter block (title, impact, summary, wcag, deque) and is
split at ``## `` headings. The platform sections (WordPress, Canvas, GitHub Pages, Plain
HTML) become tabs in the app; every other section is shown in file order.
"""
import re
from pathlib import Path

GUIDES_DIR = Path(__file__).resolve().parent.parent / 'guides'
RULE_ID = re.compile(r'^[a-z0-9][a-z0-9-]{0,99}$')
PLATFORMS = (
    ('wordpress', 'WordPress'),
    ('canvas', 'Canvas'),
    ('github-pages', 'GitHub Pages'),
    ('html', 'Plain HTML'),
)
_PLATFORM_BY_HEADING = {label.lower(): (platform_id, label) for platform_id, label in PLATFORMS}
_PLATFORM_ORDER = {platform_id: index for index, (platform_id, _) in enumerate(PLATFORMS)}


def available_guides(directory: Path | None = None) -> frozenset:
    """Rule ids that have a guide file (``region.md`` -> ``region``)."""
    directory = directory or GUIDES_DIR
    if not directory.is_dir():
        return frozenset()
    return frozenset(path.stem for path in directory.glob('*.md') if RULE_ID.match(path.stem))


def _front_matter(text: str) -> tuple[dict, str]:
    if not text.startswith('---'):
        return {}, text
    end = text.find('\n---', 3)
    if end == -1:
        return {}, text
    meta = {}
    for line in text[3:end].strip().splitlines():
        key, sep, value = line.partition(':')
        if sep:
            meta[key.strip()] = value.strip()
    return meta, text[end + 4:].lstrip('\n')


def _slug(heading: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', heading.lower()).strip('-')


def parse_guide(rule_id: str, text: str) -> dict:
    """Front matter plus the body split at ``## `` headings into common sections and
    platform tabs. Headings inside fenced code blocks are left alone."""
    meta, body = _front_matter(text)
    sections, platforms = [], []
    heading, lines, in_code = None, [], False

    def flush():
        if heading is None:
            return
        markdown = '\n'.join(lines).strip()
        platform = _PLATFORM_BY_HEADING.get(heading.lower())
        if platform:
            platforms.append({'id': platform[0], 'label': platform[1], 'markdown': markdown})
        else:
            sections.append({'id': _slug(heading), 'heading': heading, 'markdown': markdown})

    for line in body.splitlines():
        if line.startswith('```'):
            in_code = not in_code
        if not in_code and line.startswith('## '):
            flush()
            heading, lines = line[3:].strip(), []
        elif heading is not None:
            lines.append(line)
    flush()
    platforms.sort(key=lambda platform: _PLATFORM_ORDER[platform['id']])
    return {
        'rule_id': rule_id,
        'title': meta.get('title') or rule_id,
        'impact': meta.get('impact') or None,
        'summary': meta.get('summary', ''),
        'wcag': [item.strip() for item in meta.get('wcag', '').split(',') if item.strip()],
        'deque': meta.get('deque') or None,
        'markdown': body,
        'sections': sections,
        'platforms': platforms,
    }


def load_guide(rule_id: str, directory: Path | None = None) -> dict | None:
    """None for an unknown or malformed id; the id is checked before the filesystem is."""
    if not RULE_ID.match(rule_id or ''):
        return None
    path = (directory or GUIDES_DIR) / f'{rule_id}.md'
    if not path.is_file():
        return None
    return parse_guide(rule_id, path.read_text(encoding='utf-8'))


def guide_index(directory: Path | None = None) -> list[dict]:
    """``[{rule_id, title, impact, summary}]`` for every guide, sorted by title."""
    items = []
    for rule_id in available_guides(directory):
        guide = load_guide(rule_id, directory)
        if guide:
            items.append({key: guide[key] for key in ('rule_id', 'title', 'impact', 'summary')})
    return sorted(items, key=lambda item: item['title'].lower())

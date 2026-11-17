"""Manual reviews: the checklist of things automated scanning cannot check, validating
submitted results, and the prompt that lets an agent carry out a review.

Automated rules find only part of the WCAG failures on a page. The rest (keyboard use, focus
order, screen reader experience, zoom and reflow, captions, error handling) need a
person, or an agent driving a real browser, to try the website.
"""
from models.compliance import REVIEW_RESULTS
from models.website import Site, Website

# key, title, WCAG success criteria, how to test.
CHECKLIST = (
    ('keyboard', 'Everything works with the keyboard alone', '2.1.1, 2.1.2',
     'Using only Tab, Shift+Tab, Enter, Space and the arrow keys, reach and operate every link, button, menu, '
     'form field and widget. Nothing may trap focus.'),
    ('focus-visible', 'Keyboard focus is always visible', '2.4.7, 2.4.11',
     'While tabbing, the focused element always has a clearly visible indicator that is not hidden behind '
     'sticky headers or other content.'),
    ('focus-order', 'Focus order follows the visual order', '2.4.3',
     'Tabbing moves through the page in an order that matches its reading order; dialogs move focus into '
     'themselves and back when closed.'),
    ('skip-link', 'A way to skip repeated navigation', '2.4.1',
     'A "skip to main content" link, or landmarks/headings, lets keyboard and screen reader users bypass the '
     'navigation.'),
    ('screen-reader', 'Content makes sense with a screen reader', '1.3.1, 4.1.2',
     'With NVDA, JAWS or VoiceOver: headings, landmarks, links, buttons and form fields are announced with '
     'meaningful names and roles; images are described or skipped as appropriate.'),
    ('headings', 'Headings outline the page', '1.3.1, 2.4.6',
     'Headings describe their sections and their levels form a sensible outline without skipped levels used '
     'for styling.'),
    ('zoom', 'Text resizes to 200% without loss', '1.4.4',
     'At 200% browser zoom all content and functions remain available, with nothing cut off or overlapping.'),
    ('reflow', 'Content reflows at 320 CSS pixels', '1.4.10',
     'At 400% zoom (or a 320px-wide window) content fits in one column without horizontal scrolling, except '
     'data tables, maps and similar.'),
    ('text-spacing', 'Text spacing can be increased', '1.4.12',
     'With increased line, paragraph, letter and word spacing (WCAG 1.4.12 values) no text is cut off or '
     'overlaps.'),
    ('forms', 'Forms are labelled and errors are clear', '1.3.1, 3.3.1, 3.3.2, 3.3.3',
     'Every field has a visible label; required fields are indicated; submitting with mistakes identifies the '
     'field, says what is wrong in text, and suggests a fix.'),
    ('media', 'Video has captions, audio has transcripts', '1.2.1, 1.2.2, 1.2.5',
     'Pre-recorded video has accurate synchronized captions (and audio description where the visuals carry '
     'information); audio-only content has a transcript.'),
    ('motion', 'Moving content can be paused', '2.2.2, 2.3.1',
     'Carousels, auto-playing video and animations that last more than five seconds can be paused or stopped; '
     'nothing flashes more than three times a second.'),
    ('timing', 'Time limits can be extended', '2.2.1',
     'Any session timeout or time limit warns the user and lets them extend it.'),
    ('color-meaning', 'Color is not the only way information is shown', '1.4.1',
     'Links in text, required fields, errors, chart series and status indicators are distinguishable without '
     'color (underline, icon, text, pattern).'),
    ('link-purpose', 'Link and button text says where it goes', '2.4.4',
     'Links and buttons make sense out of context or from their surrounding sentence; no unexplained "click '
     'here" or "read more".'),
    ('documents', 'Linked documents are accessible', '1.3.1, 2.4.2, 3.1.1',
     'PDFs and Office documents are tagged, have a title and language, a logical reading order, and alt text; '
     'or an accessible alternative is offered.'),
)
CHECKLIST_KEYS = tuple(item[0] for item in CHECKLIST)
MAX_PAGES = 20


def checklist() -> list:
    return [{'key': key, 'title': title, 'wcag': wcag, 'how': how} for key, title, wcag, how in CHECKLIST]


def clean_results(results) -> dict:
    """Validate submitted results: ``{key: {'result', 'notes', 'pages'}}`` with known
    keys and results. Raises ValueError."""
    if results is None:
        return {}
    if not isinstance(results, dict):
        raise ValueError('results must be an object keyed by checklist item')
    cleaned = {}
    for key, entry in results.items():
        if key not in CHECKLIST_KEYS:
            raise ValueError(f"'{key}' is not a checklist item")
        if isinstance(entry, str):
            entry = {'result': entry}
        if not isinstance(entry, dict) or entry.get('result') not in REVIEW_RESULTS:
            raise ValueError(f"{key}: result must be one of {', '.join(REVIEW_RESULTS)}")
        notes = entry.get('notes')
        if notes is not None and not isinstance(notes, str):
            raise ValueError(f'{key}: notes must be a string')
        pages = entry.get('pages') or []
        if not isinstance(pages, list) or not all(isinstance(p, str) for p in pages):
            raise ValueError(f'{key}: pages must be a list of URLs')
        cleaned[key] = {'result': entry['result'], 'notes': (notes or '').strip()[:5000] or None, 'pages': pages[:MAX_PAGES]}
    return cleaned


def clean_pages(pages) -> list:
    if pages is None:
        return []
    if not isinstance(pages, list) or not all(isinstance(p, str) for p in pages):
        raise ValueError('pages must be a list of URLs')
    return [p.strip()[:1000] for p in pages if p.strip()][:MAX_PAGES]


def save_review(review, data: dict, now) -> None:
    """Apply a create/update body to ``review`` (not committed). Raises ValueError."""
    from models.compliance import REVIEW_STATUSES  # local import: keeps the module header short
    if 'results' in data:
        merged = dict(review.results or {})
        merged.update(clean_results(data['results']))
        review.results = merged
    if 'pages' in data:
        review.pages = clean_pages(data['pages'])
    if 'summary' in data:
        if data['summary'] is not None and not isinstance(data['summary'], str):
            raise ValueError('summary must be a string')
        review.summary = (data['summary'] or '').strip()[:10000] or None
    if 'tool' in data:
        if data['tool'] is not None and not isinstance(data['tool'], str):
            raise ValueError('tool must be a string')
        review.tool = (data['tool'] or '').strip()[:200] or None
    if 'status' in data:
        if data['status'] not in REVIEW_STATUSES:
            raise ValueError(f"status must be one of {', '.join(REVIEW_STATUSES)}")
        review.status = data['status']
        review.completed_at = now if data['status'] == 'completed' else None


def suggested_pages(website: Website, limit: int = 8) -> list:
    """Pages worth reviewing: the home page, then the shallowest pages (the main
    sections, which usually share templates with the rest)."""
    urls = [row.url for row in website.sites.with_entities(Site.url).all()]
    root = website.url.rstrip('/')
    urls.sort(key=lambda url: (url.rstrip('/') != root, url.rstrip('/').count('/'), len(url), url))
    if not urls:
        urls = [website.url]
    return urls[:limit]


def agent_prompt(website: Website, api_base: str, pages: list | None = None) -> str:
    """Instructions for an agent with a real browser and an API key to review the
    website against the checklist and submit the result."""
    pages = pages or suggested_pages(website)
    items = '\n'.join(
        f"{index}. `{key}` — **{title}** (WCAG {wcag}). {how}"
        for index, (key, title, wcag, how) in enumerate(CHECKLIST, start=1))
    page_list = '\n'.join(f'- {url}' for url in pages)
    example_results = ',\n'.join(
        f'      "{key}": {{"result": "pass", "notes": "", "pages": []}}' for key in CHECKLIST_KEYS[:2])
    return f"""# Manual accessibility review of {website.url}

You are reviewing a website for accessibility problems that automated scanners cannot
find. Use a real browser you can drive (keyboard input, zoom, window resizing, reading
the accessibility tree). Do not submit forms that send data, buy, delete, or post
anything; stop at the last step before submission. Stay on {website.url}.

## Pages to test

{page_list}

Test each page above against every checklist item. Add other pages if a template or
widget you have not seen yet appears (for example a search results page or a form).

## Checklist

{items}

For each item decide one result:
- `pass` — works on every page tested
- `fail` — fails on at least one page; say where and what happens in `notes`, list the pages in `pages`
- `not_applicable` — the pages have nothing this item applies to (e.g. no video)
- `not_tested` — you could not test it; say why in `notes`

Write notes a web developer can act on: the page, the element (visible text or a CSS
selector), what you did, what happened, and what should happen.

## Submit the result

When finished, send one request (replace YOUR_API_KEY with the key you were given):

```
POST {api_base}/api/v1/websites/{website.id}/reviews
X-API-Key: YOUR_API_KEY
Content-Type: application/json

{{
  "status": "completed",
  "tool": "<your name and version>",
  "pages": [<the page URLs you tested>],
  "summary": "<two or three sentences: the most important problems first>",
  "results": {{
{example_results},
      ...one entry for each of: {', '.join(CHECKLIST_KEYS)}
  }}
}}
```

A 201 response means the review was recorded. A 400 response names the field to fix.
"""

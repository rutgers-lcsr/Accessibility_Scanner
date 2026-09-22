"""Document inventory: the PDF, Word, PowerPoint and Excel files a website links to,
with basic accessibility checks on its own PDFs.

The crawler collects document links per page (scanner.browser.parse) and hands the
whole map to sync_documents after the crawl; check_website_documents then downloads
the website's own PDFs (bounded by size, count and robots.txt) and reads what a
screen reader would need: is the PDF tagged, does it have a title and a language.
"""
import io
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin, urlparse

import requests

from models import db
from models.document import Document
from models.settings import Settings
from models.website import Site, Website
from scanner.browser.report import ACCESSIBILITY_USER_AGENT
from scanner.log import log_message
from utils.urls import get_netloc, is_safe_target

MAX_REDIRECTS = 5
CHECKABLE = ('pending', 'tagged', 'untagged', 'unreachable', 'too_large', 'unreadable')


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _int_setting(key: str, minimum: int) -> int:
    try:
        return max(minimum, int(Settings.get(key)))
    except (TypeError, ValueError):
        return minimum


def document_settings() -> dict:
    return {
        'max_bytes': _int_setting('document_max_size_mb', 1) * 1024 * 1024,
        'per_scan': _int_setting('document_checks_per_scan', 0),
        'recheck_days': _int_setting('document_recheck_days', 1),
    }


# --- inventory ---------------------------------------------------------------------------


def sync_documents(website_id: int, found: dict, now: datetime | None = None) -> dict:
    """Bring the website's documents in line with what the crawl linked to.

    ``found`` is ``{url: {'type': 'pdf', 'pages': {page urls}}}``. New documents start
    ``pending`` (PDF) or ``not_checked``; known ones keep their check results and
    first_seen; documents no longer linked from any crawled page are removed (like
    pages, so a truncated crawl can drop them until the next full one).
    """
    now = now or _utcnow()
    existing = {doc.url: doc for doc in db.session.query(Document).filter_by(website_id=website_id).all()}
    page_urls = {url for info in found.values() for url in info.get('pages', ())}
    sites_by_url = {site.url: site for site in db.session.query(Site).filter(Site.url.in_(list(page_urls))).all()} if page_urls else {}
    result = {'new': 0, 'updated': 0, 'removed': 0}

    for url, info in found.items():
        doc_type = info['type']
        doc = existing.get(url)
        if doc is None:
            doc = Document(website_id=website_id, url=url, doc_type=doc_type, first_seen=now, last_seen=now,
                           status='pending' if doc_type == 'pdf' else 'not_checked')
            db.session.add(doc)
            result['new'] += 1
        else:
            doc.last_seen = now
            if doc.doc_type != doc_type:
                doc.doc_type = doc_type
                doc.status = 'pending' if doc_type == 'pdf' else 'not_checked'
            result['updated'] += 1
        doc.sites = [sites_by_url[page] for page in info.get('pages', ()) if page in sites_by_url]

    for url, doc in existing.items():
        if url not in found:
            db.session.delete(doc)
            result['removed'] += 1
    db.session.commit()
    return result


# --- PDF checks ----------------------------------------------------------------------------


def fetch_pdf(url: str, max_bytes: int) -> tuple:
    """``(bytes or None, status, error, size)``: redirects followed by hand with the
    public-host check on every hop, streamed under a size cap."""
    try:
        for _ in range(MAX_REDIRECTS + 1):
            if not is_safe_target(url):
                return None, 'unreachable', 'Refusing to fetch a non-public host', None
            response = requests.get(url, timeout=(10, 30), allow_redirects=False, stream=True,
                                    headers={'User-Agent': ACCESSIBILITY_USER_AGENT})
            try:
                if response.is_redirect or response.is_permanent_redirect:
                    location = response.headers.get('Location')
                    if not location:
                        return None, 'unreachable', 'Redirect without a location', None
                    url = urljoin(url, location)
                    continue
                if response.status_code >= 400:
                    return None, 'unreachable', f'HTTP {response.status_code}', None
                declared = response.headers.get('Content-Length')
                if declared and declared.isdigit() and int(declared) > max_bytes:
                    return None, 'too_large', f'{int(declared)} bytes, over the limit', int(declared)
                chunks, size = [], 0
                for chunk in response.iter_content(chunk_size=65536):
                    size += len(chunk)
                    if size > max_bytes:
                        return None, 'too_large', f'more than {max_bytes} bytes', size
                    chunks.append(chunk)
                return b''.join(chunks), 'fetched', None, size
            finally:
                response.close()
        return None, 'unreachable', 'Too many redirects', None
    except Exception as e:
        return None, 'unreachable', str(e)[:500], None


def inspect_pdf(data: bytes) -> dict:
    """What a screen reader needs from a PDF: tagged structure, title, language, pages."""
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data), strict=False)
        if reader.is_encrypted:
            reader.decrypt('')
        root = reader.trailer['/Root']
        mark_info = root.get('/MarkInfo')
        tagged = bool(mark_info and mark_info.get('/Marked')) or '/StructTreeRoot' in root
        language = root.get('/Lang')
        metadata = reader.metadata
        title = (metadata.title or '').strip() if metadata else ''
        return {
            'status': 'tagged' if tagged else 'untagged',
            'title': title[:500] or None,
            'has_title': bool(title),
            'language': str(language)[:32] if language else None,
            'page_count': len(reader.pages),
            'error': None,
        }
    except Exception as e:
        return {'status': 'unreadable', 'title': None, 'has_title': None, 'language': None, 'page_count': None,
                'error': str(e)[:500]}


def check_website_documents(website_id: int, robots=None, crawl_delay: float = 0.0, now: datetime | None = None) -> int:
    """Check the website's own PDFs: pending ones first, then ones whose check is older
    than document_recheck_days, up to document_checks_per_scan. Returns how many were
    checked. Documents on other hosts stay not_checked."""
    from scanner.scan import ROBOTS_AGENT, commit_with_retry  # local import: scanner imports services

    settings = document_settings()
    if settings['per_scan'] <= 0:
        return 0
    now = now or _utcnow()
    website = db.session.get(Website, website_id)
    if website is None:
        return 0
    host = get_netloc(website.url).lower()
    stale = now - timedelta(days=settings['recheck_days'])

    candidates = (
        db.session.query(Document)
        .filter(Document.website_id == website_id, Document.doc_type == 'pdf', Document.status.in_(CHECKABLE))
        .order_by(Document.checked_at.isnot(None), Document.checked_at.asc(), Document.id.asc())
        .all()
    )
    checked = 0
    for doc in candidates:
        if checked >= settings['per_scan']:
            break
        if doc.checked_at is not None and doc.checked_at >= stale:
            continue
        if get_netloc(doc.url).lower() != host:
            doc.status = 'not_checked'
            doc.error = 'Hosted elsewhere; not checked'
            commit_with_retry()
            continue
        if robots is not None and not robots.can_fetch(ROBOTS_AGENT, doc.url):
            doc.status, doc.error, doc.checked_at = 'skipped', 'Disallowed by robots.txt', now
            commit_with_retry()
            continue
        if crawl_delay:
            time.sleep(crawl_delay)
        data, status, error, size = fetch_pdf(doc.url, settings['max_bytes'])
        doc.checked_at = now
        doc.size_bytes = size
        if data is None:
            doc.status, doc.error = status, error
        else:
            result = inspect_pdf(data)
            doc.status = result['status']
            doc.error = result['error']
            doc.title, doc.has_title = result['title'], result['has_title']
            doc.language, doc.page_count = result['language'], result['page_count']
        checked += 1
        commit_with_retry()
    if checked:
        log_message(f"Checked {checked} documents for {website.url}", 'info')
    return checked


# --- counts -----------------------------------------------------------------------------------


def empty_document_counts() -> dict:
    return {'total': 0, 'pdf': 0, 'untagged_pdf': 0, 'unchecked': 0}


def document_counts(website_ids) -> dict:
    """``{website_id: {total, pdf, untagged_pdf, unchecked}}`` in one grouped query."""
    from sqlalchemy import func

    counts = {}
    if not website_ids:
        return counts
    rows = (
        db.session.query(Document.website_id, Document.doc_type, Document.status, func.count(Document.id))
        .filter(Document.website_id.in_(list(website_ids)))
        .group_by(Document.website_id, Document.doc_type, Document.status)
        .all()
    )
    for website_id, doc_type, status, count in rows:
        entry = counts.setdefault(website_id, empty_document_counts())
        entry['total'] += count
        if doc_type == 'pdf':
            entry['pdf'] += count
            if status == 'untagged':
                entry['untagged_pdf'] += count
            elif status == 'pending':
                entry['unchecked'] += count
    return counts

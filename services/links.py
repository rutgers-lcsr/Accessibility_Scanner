"""Broken-link check: every http(s) link a website's pages carry, on its own host or
elsewhere, probed after the crawl.

The crawler collects link targets per page (scanner.browser.parse) and hands the whole
map to sync_links after the crawl; check_website_links then probes each target (HEAD,
falling back to GET, redirects followed by hand with the public-host check on every
hop) a few hosts at a time, one request at a time per host.
"""
import socket
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin, urlparse

import requests

from models import db
from models.link import Link, LinkSource
from models.settings import Settings
from models.website import Site, Website
from sqlalchemy.orm import selectinload
from scanner.browser.report import ACCESSIBILITY_USER_AGENT
from scanner.log import log_message
from utils.urls import get_netloc, is_safe_target

MAX_REDIRECTS = 5
HOST_WORKERS = 8
# Link.url / Link.final_url column width; longer hrefs are not recorded.
MAX_URL_LENGTH = 1000
# Login walls and bot protection: the link may well work for a person.
BLOCKED_CODES = (401, 403, 429, 999)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _int_setting(key: str, minimum: int) -> int:
    try:
        return max(minimum, int(Settings.get(key)))
    except (TypeError, ValueError):
        return minimum


def link_settings() -> dict:
    return {
        'per_scan': _int_setting('link_checks_per_scan', 0),
        'recheck_days': _int_setting('link_recheck_days', 1),
    }


# --- inventory ---------------------------------------------------------------------------


def sync_links(website_id: int, found: dict, now: datetime | None = None) -> dict:
    """Bring the website's links in line with what the crawl found.

    ``found`` is ``{url: {page url: link text}}``. New links start ``pending``; known
    ones keep their check results and first_seen; links no longer on any crawled page
    are removed (like documents, so a truncated crawl can drop them until the next full
    one).
    """
    now = now or _utcnow()
    website = db.session.get(Website, website_id)
    if website is None:
        return {'new': 0, 'updated': 0, 'removed': 0}
    host = get_netloc(website.url).lower()
    # Keyed case-insensitively: MariaDB's default collation treats /Contact and /contact
    # as the same unique key, so they must be one row here too (first spelling kept).
    wanted: dict[str, tuple[str, dict]] = {}
    for url, pages in found.items():
        if len(url) > MAX_URL_LENGTH:
            continue
        key = url.lower()
        if key in wanted:
            wanted[key][1].update(pages)
        else:
            wanted[key] = (url, dict(pages))
    existing = {link.url.lower(): link for link in
                db.session.query(Link).options(selectinload(Link.sources)).filter_by(website_id=website_id).all()}
    page_urls = {url for _, pages in wanted.values() for url in pages}
    sites_by_url = {site.url: site for site in db.session.query(Site).filter(Site.url.in_(list(page_urls))).all()} if page_urls else {}
    result = {'new': 0, 'updated': 0, 'removed': 0}

    for key, (url, pages) in wanted.items():
        link = existing.get(key)
        if link is None:
            link = Link(website_id=website_id, url=url, first_seen=now, last_seen=now, status='pending',
                        external=get_netloc(url).lower() != host)
            db.session.add(link)
            result['new'] += 1
        else:
            link.last_seen = now
            result['updated'] += 1
        # Updated in place: replacing the list would delete and re-insert the same
        # (link, site) key in one flush.
        wanted_sources = {sites_by_url[page].id: (text or None) for page, text in pages.items() if page in sites_by_url}
        for source in list(link.sources):
            if source.site_id in wanted_sources:
                source.text = wanted_sources.pop(source.site_id)
            else:
                link.sources.remove(source)
        for site_id, text in wanted_sources.items():
            link.sources.append(LinkSource(site_id=site_id, text=text))

    for key, link in existing.items():
        if key not in wanted:
            db.session.delete(link)
            result['removed'] += 1
    db.session.commit()
    return result


# --- probing -------------------------------------------------------------------------------


def _classify(status_code: int) -> str:
    if status_code in BLOCKED_CODES:
        return 'blocked'
    if status_code >= 500:
        return 'error'
    if status_code >= 400:
        return 'broken'
    return 'ok'


def fetch_link(url: str) -> tuple:
    """``(status, status_code, final_url, error)``: HEAD first, GET (body unread) when
    the server rejects HEAD; redirects followed by hand with the public-host check on
    every hop. ``final_url`` is set only when the link redirected."""
    start = url
    try:
        for _ in range(MAX_REDIRECTS + 1):
            if not is_safe_target(url):
                # is_safe_target also fails when the host does not resolve; a dead
                # domain is a broken link, not something to hide as skipped.
                if not _host_resolves(url):
                    return 'error', None, None, 'DNS lookup failed'
                return 'skipped', None, None, 'Refusing to probe a non-public host'
            code, location = _probe(url)
            if location is not None:
                if not location:
                    return 'error', code, None, 'Redirect without a location'
                url = urljoin(url, location)
                continue
            final_url = url[:MAX_URL_LENGTH] if url != start else None
            return _classify(code), code, final_url, (None if code < 400 else f'HTTP {code}')
        return 'error', None, url[:MAX_URL_LENGTH], 'Too many redirects'
    except Exception as e:
        return 'error', None, None, f'{type(e).__name__}: {e}'[:500]


def _host_resolves(url: str) -> bool:
    try:
        socket.getaddrinfo(urlparse(url).hostname, None)
        return True
    except (socket.gaierror, UnicodeError, TypeError, ValueError):
        return False


def _probe(url: str) -> tuple:
    """``(status code, redirect location or None)`` for one hop."""
    headers = {'User-Agent': ACCESSIBILITY_USER_AGENT}
    response = requests.head(url, timeout=(5, 10), allow_redirects=False, headers=headers)
    try:
        if response.status_code < 400:
            return _hop(response)
    finally:
        response.close()
    # Many servers answer HEAD with 405 (or 404, 403); a GET tells whether the link works.
    response = requests.get(url, timeout=(5, 10), allow_redirects=False, stream=True, headers=headers)
    try:
        return _hop(response)
    finally:
        response.close()


def _hop(response) -> tuple:
    """``(status code, Location or '' for a redirect, None otherwise)``. Any 3xx counts as
    a redirect: requests sets is_redirect only when a Location header is present, and a
    3xx without one must not pass as a working link."""
    if 300 <= response.status_code < 400:
        return response.status_code, response.headers.get('Location') or ''
    return response.status_code, None


def check_website_links(website_id: int, robots=None, crawl_delay: float = 0.0, now: datetime | None = None) -> int:
    """Probe the website's links: pending ones first, then ones whose check is older than
    link_recheck_days, up to link_checks_per_scan. Returns how many were probed.

    Targets are grouped by host; up to HOST_WORKERS hosts are probed at once, and within
    a host one request at a time with ``crawl_delay`` between them. ``robots`` applies
    to the website's own host only; other hosts get one request per link, as a visitor
    clicking it would."""
    from scanner.scan import ROBOTS_AGENT, commit_with_retry  # local import: scanner imports services

    settings = link_settings()
    if settings['per_scan'] <= 0:
        return 0
    now = now or _utcnow()
    website = db.session.get(Website, website_id)
    if website is None:
        return 0
    host = get_netloc(website.url).lower()
    stale = now - timedelta(days=settings['recheck_days'])

    candidates = (
        db.session.query(Link)
        .filter(Link.website_id == website_id)
        # Never-checked first, then off-site before same-site (the crawl itself already
        # visited most same-site targets), then the oldest checks.
        .order_by(Link.checked_at.isnot(None), Link.external.desc(), Link.checked_at.asc(), Link.id.asc())
        .all()
    )
    by_host: dict[str, list] = defaultdict(list)
    queued = 0
    for link in candidates:
        if queued >= settings['per_scan']:
            break
        if link.checked_at is not None and link.checked_at >= stale:
            continue
        if robots is not None and not link.external and not robots.can_fetch(ROBOTS_AGENT, link.url):
            link.status, link.status_code, link.final_url, link.error, link.checked_at = 'skipped', None, None, 'Disallowed by robots.txt', now
            commit_with_retry()
            continue
        by_host[get_netloc(link.url).lower()].append((link.id, link.url))
        queued += 1
    if not by_host:
        return 0

    def probe_host(targets):
        results = []
        for index, (link_id, url) in enumerate(targets):
            if crawl_delay and index:
                time.sleep(crawl_delay)
            results.append((link_id, fetch_link(url)))
        return results

    # Worker threads only do HTTP (plain ids and urls, no session); the rows are
    # written here, one commit per host.
    checked = 0
    with ThreadPoolExecutor(max_workers=HOST_WORKERS) as pool:
        for results in pool.map(probe_host, by_host.values()):
            for link_id, (status, code, final_url, error) in results:
                link = db.session.get(Link, link_id)
                link.status, link.status_code, link.final_url, link.error, link.checked_at = status, code, final_url, error, now
                checked += 1
            commit_with_retry()
    log_message(f"Checked {checked} links for {website.url}", 'info')
    return checked


# --- listing ----------------------------------------------------------------------------------


def latest_report_ids(site_ids) -> dict:
    """``{site_id: latest report id}`` in one grouped query."""
    from sqlalchemy import func

    from models.report import Report

    if not site_ids:
        return {}
    rows = (
        db.session.query(Report.site_id, func.max(Report.id))
        .filter(Report.site_id.in_(list(site_ids)))
        .group_by(Report.site_id)
        .all()
    )
    return dict(rows)


def site_links(site_id: int) -> list:
    """The links on one page with their check results, broken first, each with the text
    of the link on that page."""
    from sqlalchemy import case

    from models.link import LINK_STATUS_ORDER

    priority = case({name: index for index, name in enumerate(LINK_STATUS_ORDER)}, value=Link.status, else_=len(LINK_STATUS_ORDER))
    rows = (
        db.session.query(Link, LinkSource.text)
        .join(LinkSource, LinkSource.link_id == Link.id)
        .filter(LinkSource.site_id == site_id)
        .order_by(priority, Link.url)
        .all()
    )
    iso = lambda value: value.strftime("%Y-%m-%dT%H:%M:%SZ") if value else None
    return [{
        'id': link.id,
        'url': link.url,
        'external': link.external,
        'status': link.status,
        'status_code': link.status_code,
        'final_url': link.final_url,
        'error': link.error,
        'checked_at': iso(link.checked_at),
        'text': text,
    } for link, text in rows]


# --- counts -----------------------------------------------------------------------------------


def empty_link_counts() -> dict:
    return {'total': 0, 'broken': 0}


def link_counts(website_ids) -> dict:
    """``{website_id: {total, broken}}`` in one grouped query."""
    from sqlalchemy import func

    counts = {}
    if not website_ids:
        return counts
    rows = (
        db.session.query(Link.website_id, Link.status, func.count(Link.id))
        .filter(Link.website_id.in_(list(website_ids)))
        .group_by(Link.website_id, Link.status)
        .all()
    )
    for website_id, status, count in rows:
        entry = counts.setdefault(website_id, empty_link_counts())
        entry['total'] += count
        if status == 'broken':
            entry['broken'] += count
    return counts

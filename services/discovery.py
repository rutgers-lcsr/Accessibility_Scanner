"""Site discovery under a domain a site admin picked (models.discovery).

Sources:
- certificate transparency (crt.sh): every certificate issued for a name under the
  domain. This sends the domain name, and nothing else, to crt.sh.
- links: hosts under the domain that the crawled websites link to or load resources
  from (models.link.Link, models.inventory.ThirdPartyHost).

Each new host, and each host not probed for PROBE_EVERY_DAYS, is probed: does it
resolve, does https:// (else http://) answer, and with what page title.
"""
import json
import re
import socket
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from models import db
from models.discovery import DiscoveredHost
from models.inventory import ThirdPartyHost
from models.link import Link
from models.website import Domain, Website
from scanner.browser.report import ACCESSIBILITY_USER_AGENT
from scanner.log import log_message

CT_URL = 'https://crt.sh/'
CT_TIMEOUT = 90
PROBE_EVERY_DAYS = 7
PROBES_PER_RUN = 200
WORKERS = 8
HOST_NAME = re.compile(r'^(?=.{1,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$')


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def under(host: str, domain: str) -> bool:
    host, domain = host.lower().rstrip('.'), domain.lower().strip('.')
    return host == domain or host.endswith('.' + domain)


def clean_host(name: str) -> str | None:
    """A certificate or URL host name as a plain lower-case host, or None (wildcards
    lose their ``*.``; anything that is not a host name is dropped)."""
    name = (name or '').strip().lower().rstrip('.')
    if name.startswith('*.'):
        name = name[2:]
    return name if HOST_NAME.match(name) else None


def ct_hosts(domain: str) -> set:
    """Host names under ``domain`` from certificate transparency logs (crt.sh). Raises
    on a network or parse failure so the caller can report it."""
    response = requests.get(CT_URL, params={'q': f'%.{domain}', 'output': 'json'}, timeout=CT_TIMEOUT,
                            headers={'User-Agent': ACCESSIBILITY_USER_AGENT})
    response.raise_for_status()
    hosts = set()
    for entry in json.loads(response.text or '[]'):
        for name in str(entry.get('name_value', '')).splitlines():
            host = clean_host(name)
            if host and under(host, domain):
                hosts.add(host)
    return hosts


def link_hosts(domain: str) -> set:
    """Hosts under ``domain`` that crawled pages link to or load resources from."""
    hosts = set()
    pattern = f'%{domain.lower()}%'
    for (url,) in db.session.query(Link.url).filter(Link.url.ilike(pattern)).all():
        host = clean_host(urlparse(url).hostname or '')
        if host and under(host, domain):
            hosts.add(host)
    for (host,) in db.session.query(ThirdPartyHost.host).filter(ThirdPartyHost.host.ilike(pattern)).all():
        host = clean_host(host)
        if host and under(host, domain):
            hosts.add(host)
    return hosts


def probe_host(host: str) -> dict:
    """``{'resolves', 'http_status', 'final_url', 'title', 'error'}`` for one host:
    https:// first, http:// when that fails to connect."""
    from services.health import fetch_page  # local import: health imports models
    try:
        socket.getaddrinfo(host, None)
    except (socket.gaierror, UnicodeError):
        return {'resolves': False, 'http_status': None, 'final_url': None, 'title': None, 'error': 'DNS lookup failed'}
    page = fetch_page(f'https://{host}/')
    if page['status_code'] is None:
        plain = fetch_page(f'http://{host}/')
        if plain['status_code'] is not None:
            page = plain
    title = None
    if page['html']:
        tag = BeautifulSoup(page['html'], 'html.parser').find('title')
        title = tag.get_text(' ', strip=True)[:300] if tag else None
    final_url = page['final_url'][:1000] if page['status_code'] and page['final_url'] else None
    return {
        'resolves': True,
        'http_status': page['status_code'],
        'final_url': final_url,
        'title': title,
        'error': page['error'],
    }


def tracked_hosts() -> dict:
    """``{host: website id}`` for every website's host."""
    out = {}
    for website_id, url in db.session.query(Website.id, Website.url).all():
        host = (urlparse(url).hostname or '').lower()
        if host:
            out.setdefault(host, website_id)
    return out


def tracked_website_id(host: str, tracked: dict) -> int | None:
    """A website on this host, or on its www. twin."""
    host = host.lower()
    twin = host[4:] if host.startswith('www.') else 'www.' + host
    return tracked.get(host) or tracked.get(twin)


def run_discovery(domain_id: int, now: datetime | None = None, use_ct: bool = True) -> dict:
    """Gather hosts under the domain, store new ones, probe what is due. Returns
    ``{'found', 'new', 'probed', 'ct_error'}``."""
    now = now or _utcnow()
    domain = db.session.get(Domain, domain_id)
    if domain is None:
        raise ValueError('Domain not found')
    name = domain.domain.lower().strip('.')
    sources: dict = {}
    ct_error = None
    if use_ct:
        try:
            for host in ct_hosts(name):
                sources.setdefault(host, set()).add('ct')
        except Exception as e:
            ct_error = f'{type(e).__name__}: {e}'[:300]
            log_message(f"Certificate transparency lookup for {name} failed: {ct_error}", 'warning')
    for host in link_hosts(name):
        sources.setdefault(host, set()).add('links')

    existing = {row.host: row for row in db.session.query(DiscoveredHost).filter_by(domain_id=domain_id).all()}
    new = 0
    for host, found_in in sources.items():
        row = existing.get(host)
        if row is None:
            row = DiscoveredHost(domain_id=domain_id, host=host, status='new', first_seen=now, sources='')
            db.session.add(row)
            existing[host] = row
            new += 1
        row.last_seen = now
        row.sources = ','.join(sorted(set(filter(None, (row.sources or '').split(','))) | found_in))
    db.session.commit()

    tracked = tracked_hosts()
    stale = now - timedelta(days=PROBE_EVERY_DAYS)
    due = [row for row in existing.values()
           if row.status != 'ignored' and not tracked_website_id(row.host, tracked)
           and (row.checked_at is None or row.checked_at < stale)]
    due.sort(key=lambda row: (row.checked_at is not None, row.checked_at or now, row.host))
    due = due[:PROBES_PER_RUN]
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        results = list(pool.map(probe_host, [row.host for row in due]))
    for row, result in zip(due, results):
        row.resolves = result['resolves']
        row.http_status = result['http_status']
        row.final_url = result['final_url']
        row.title = result['title']
        row.probe_error = (result['error'] or '')[:500] or None
        row.checked_at = now
    domain.discovered_at = now
    domain.discovery_error = ct_error
    db.session.commit()
    return {'found': len(sources), 'new': new, 'probed': len(due), 'ct_error': ct_error}


def discovered_rows(domain_id: int, status: str | None = None) -> list:
    """The domain's discovered hosts with whether a website covers each: live ones first."""
    tracked = tracked_hosts()
    rows = [row.to_dict(tracked_website_id(row.host, tracked))
            for row in db.session.query(DiscoveredHost).filter_by(domain_id=domain_id).all()]
    if status:
        rows = [row for row in rows if row['status'] == status]
    rank = lambda r: (0 if r['http_status'] and r['http_status'] < 400 else 1 if r['resolves'] else 2)
    rows.sort(key=lambda r: (rank(r), r['host']))
    return rows

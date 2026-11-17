"""Site health checks (see models.health).

check_website fetches the website's home page (redirects followed by hand with the
public-host check on every hop), opens a verified TLS connection, asks http:// whether
it redirects to https://, and reads the security headers, the platform and the content
requirements off the response. run_health_checks does that for every website that is
due, a few at a time, and prunes the uptime history.
"""
import re
import socket
import ssl
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from models import db
from models.health import HealthCheck, WebsiteHealth
from models.settings import Settings
from models.website import Website
from scanner.browser.report import ACCESSIBILITY_USER_AGENT
from scanner.log import log_message
from utils.urls import is_safe_target

MAX_REDIRECTS = 5
TIMEOUT = (5, 15)
MAX_BODY_BYTES = 2 * 1024 * 1024
WORKERS = 8

# Header name -> what it protects against; the frontend shows the same list.
SECURITY_HEADERS = (
    'Strict-Transport-Security',
    'Content-Security-Policy',
    'X-Content-Type-Options',
    'X-Frame-Options',
    'Referrer-Policy',
    'Permissions-Policy',
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _int_setting(key: str, minimum: int) -> int:
    try:
        return max(minimum, int(Settings.get(key)))
    except (TypeError, ValueError):
        return minimum


# --- fetching ------------------------------------------------------------------------------


def fetch_page(url: str) -> dict:
    """GET ``url`` following redirects by hand (public hosts only). Returns ``{'up',
    'status_code', 'response_ms', 'final_url', 'headers', 'html', 'error'}``; a page is
    up when it answers below 400."""
    result = {'up': False, 'status_code': None, 'response_ms': None, 'final_url': url,
              'headers': {}, 'html': '', 'error': None}
    started = time.monotonic()
    try:
        for _ in range(MAX_REDIRECTS + 1):
            if not is_safe_target(url):
                result['error'] = 'The host does not resolve to a public address'
                return result
            response = requests.get(url, timeout=TIMEOUT, allow_redirects=False, stream=True,
                                    headers={'User-Agent': ACCESSIBILITY_USER_AGENT})
            try:
                if 300 <= response.status_code < 400 and response.headers.get('Location'):
                    url = urljoin(url, response.headers['Location'])
                    continue
                result['status_code'] = response.status_code
                result['final_url'] = url
                result['headers'] = dict(response.headers)
                body = response.raw.read(MAX_BODY_BYTES, decode_content=True) or b''
                result['response_ms'] = int((time.monotonic() - started) * 1000)
                result['html'] = body.decode(response.encoding or 'utf-8', errors='replace')
                result['up'] = response.status_code < 400
                if not result['up']:
                    result['error'] = f'HTTP {response.status_code}'
                return result
            finally:
                response.close()
        result['error'] = 'Too many redirects'
    except Exception as e:
        result['error'] = f'{type(e).__name__}: {e}'[:500]
    return result


def check_https_redirect(url: str) -> bool | None:
    """Whether http:// on the website's host redirects to https://; None when the
    plain-http request fails (port 80 closed counts as no redirect)."""
    host = urlparse(url).hostname
    if not host:
        return None
    plain = f'http://{host}/'
    if not is_safe_target(plain):
        return None
    try:
        response = requests.get(plain, timeout=TIMEOUT, allow_redirects=False, stream=True,
                                headers={'User-Agent': ACCESSIBILITY_USER_AGENT})
        response.close()
    except requests.ConnectionError:
        return False
    except Exception:
        return None
    location = response.headers.get('Location') or ''
    return 300 <= response.status_code < 400 and urljoin(plain, location).startswith('https://')


def check_tls(url: str) -> dict:
    """Verified TLS handshake with the website's host: ``{'valid', 'expires_at',
    'issuer', 'error'}``. An http:// website has no certificate (valid False)."""
    parsed = urlparse(url)
    if parsed.scheme != 'https' or not parsed.hostname:
        return {'valid': False, 'expires_at': None, 'issuer': None, 'error': 'The website is not served over HTTPS'}
    if not is_safe_target(url):
        return {'valid': None, 'expires_at': None, 'issuer': None, 'error': 'The host does not resolve to a public address'}
    context = ssl.create_default_context()
    try:
        with socket.create_connection((parsed.hostname, parsed.port or 443), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=parsed.hostname) as tls:
                cert = tls.getpeercert()
    except ssl.SSLCertVerificationError as e:
        return {'valid': False, 'expires_at': None, 'issuer': None, 'error': (e.verify_message or str(e))[:500]}
    except Exception as e:
        return {'valid': None, 'expires_at': None, 'issuer': None, 'error': f'{type(e).__name__}: {e}'[:500]}
    expires = cert.get('notAfter')
    issuer = dict(item[0] for item in cert.get('issuer', ()) if item)
    return {
        'valid': True,
        'expires_at': datetime.fromtimestamp(ssl.cert_time_to_seconds(expires), tz=timezone.utc).replace(tzinfo=None) if expires else None,
        'issuer': (issuer.get('organizationName') or issuer.get('commonName') or '')[:300] or None,
        'error': None,
    }


# --- reading the page -----------------------------------------------------------------------


def security_headers(headers: dict) -> dict:
    """``{header: value or None}`` for SECURITY_HEADERS (case-insensitive). A CSP with
    frame-ancestors stands in for X-Frame-Options."""
    lower = {key.lower(): value for key, value in (headers or {}).items()}
    found = {name: lower.get(name.lower()) for name in SECURITY_HEADERS}
    csp = found.get('Content-Security-Policy') or ''
    if not found['X-Frame-Options'] and 'frame-ancestors' in csp.lower():
        found['X-Frame-Options'] = 'CSP frame-ancestors'
    return found


# (platform, regex over the HTML) tried in order after the generator meta and headers.
_HTML_MARKERS = (
    ('WordPress', re.compile(r'/wp-(?:content|includes)/', re.I)),
    ('Drupal', re.compile(r'drupal-settings-json|/sites/(?:default|all)/(?:files|themes|modules)/|Drupal\.settings', re.I)),
    ('Joomla', re.compile(r'/media/jui/|/components/com_', re.I)),
    ('Squarespace', re.compile(r'static\d*\.squarespace\.com', re.I)),
    ('Wix', re.compile(r'static\.wixstatic\.com|wix-code', re.I)),
    ('Google Sites', re.compile(r'sites\.google\.com/|www\.gstatic\.com/sites/', re.I)),
    ('Next.js', re.compile(r'__NEXT_DATA__|/_next/static/', re.I)),
    ('Nuxt', re.compile(r'__NUXT__|/_nuxt/', re.I)),
    ('Gatsby', re.compile(r'___gatsby', re.I)),
    ('Docusaurus', re.compile(r'docusaurus', re.I)),
    ('MkDocs', re.compile(r'mkdocs', re.I)),
    ('Sphinx', re.compile(r'_static/sphinx_|sphinx-rtd-theme|searchindex\.js', re.I)),
)
_GENERATOR_VERSION = re.compile(r'^\s*([A-Za-z][\w .\-]*?)\s+v?(\d[\w.\-]*)')


def fingerprint(headers: dict, html: str) -> dict:
    """Best guess at what the website runs on: ``{'platform', 'version', 'server'}``.
    The generator meta tag and X-Generator header win; then well-known paths in the
    HTML; X-Powered-By last."""
    lower = {key.lower(): value for key, value in (headers or {}).items()}
    server = (lower.get('server') or '')[:200] or None
    generator = lower.get('x-generator')
    if not generator and html:
        soup = BeautifulSoup(html, 'html.parser')
        meta = soup.find('meta', attrs={'name': re.compile('^generator$', re.I)})
        generator = meta.get('content') if meta else None
    if generator:
        generator = generator.strip()
        match = _GENERATOR_VERSION.match(generator)
        if match:
            return {'platform': match.group(1).strip()[:100], 'version': match.group(2)[:100], 'server': server}
        return {'platform': generator.split(' ')[0][:100] or generator[:100], 'version': None, 'server': server}
    if lower.get('x-drupal-cache') or lower.get('x-drupal-dynamic-cache'):
        return {'platform': 'Drupal', 'version': None, 'server': server}
    for name, pattern in _HTML_MARKERS:
        if html and pattern.search(html):
            return {'platform': name, 'version': None, 'server': server}
    powered = lower.get('x-powered-by')
    if powered:
        return {'platform': powered.split('/')[0][:100], 'version': None, 'server': server}
    return {'platform': None, 'version': None, 'server': server}


def check_requirement(requirement, soup: BeautifulSoup) -> dict:
    """Whether the page meets one ContentRequirement: ``{'id', 'name', 'passed', 'detail'}``."""
    result = {'id': requirement.id, 'name': requirement.name, 'passed': False, 'detail': None}
    try:
        if requirement.check_type == 'selector':
            found = soup.select_one(requirement.pattern)
            result['passed'] = found is not None
            result['detail'] = (found.get_text(' ', strip=True)[:200] or str(found)[:200]) if found else None
            return result
        pattern = re.compile(requirement.pattern, re.I)
        if requirement.check_type == 'text':
            match = pattern.search(soup.get_text(' ', strip=True))
            result['passed'] = match is not None
            result['detail'] = match.group(0)[:200] if match else None
            return result
        for anchor in soup.find_all('a', href=True):
            value = anchor.get_text(' ', strip=True) if requirement.check_type == 'link_text' else anchor['href']
            if pattern.search(value or ''):
                result['passed'] = True
                result['detail'] = f"{anchor.get_text(' ', strip=True)[:100]} → {anchor['href'][:200]}"
                return result
    except (re.error, ValueError, NotImplementedError) as e:
        result['detail'] = f'Invalid pattern: {e}'[:200]
    return result


# --- checking ----------------------------------------------------------------------------------


def probe_website(url: str, requirements: list) -> dict:
    """Everything a health check learns about ``url``, without touching the database
    (so it can run in a worker thread). ``requirements`` are detached copies with
    id, name, check_type and pattern."""
    page = fetch_page(url)
    found = {'page': page, 'tls': check_tls(url), 'https_redirect': check_https_redirect(url)}
    found['headers'] = security_headers(page['headers']) if page['status_code'] else {}
    found['fingerprint'] = fingerprint(page['headers'], page['html']) if page['up'] else None
    if page['up'] and requirements:
        soup = BeautifulSoup(page['html'], 'html.parser')
        found['requirements'] = [check_requirement(requirement, soup) for requirement in requirements]
    else:
        found['requirements'] = None
    return found


def record_health(website: Website, found: dict, now: datetime) -> WebsiteHealth:
    """Store a probe: append the uptime row and overwrite the latest picture. Fields a
    failed fetch cannot know (platform, requirements) keep their last values."""
    page = found['page']
    db.session.add(HealthCheck(website_id=website.id, checked_at=now, up=page['up'], status_code=page['status_code'],
                               response_ms=page['response_ms'], error=page['error']))
    health = db.session.get(WebsiteHealth, website.id)
    if health is None:
        health = WebsiteHealth(website_id=website.id, checked_at=now, up=page['up'], up_changed_at=now)
        db.session.add(health)
    elif health.up != page['up']:
        health.up_changed_at = now
    health.checked_at = now
    health.up = page['up']
    health.status_code = page['status_code']
    health.response_ms = page['response_ms']
    health.error = page['error']
    health.final_url = (page['final_url'] or '')[:1000] or None
    tls = found['tls']
    health.tls_valid, health.tls_expires_at, health.tls_issuer, health.tls_error = (
        tls['valid'], tls['expires_at'], tls['issuer'], tls['error'])
    health.https_redirect = found['https_redirect']
    if found['headers']:
        health.security_headers = found['headers']
    if found['fingerprint']:
        health.platform = found['fingerprint']['platform']
        health.platform_version = found['fingerprint']['version']
        health.server = found['fingerprint']['server']
    if found['requirements'] is not None:
        health.requirements = found['requirements']
    elif not website.requirements:
        health.requirements = []
    return health


class _Requirement:
    """A detached copy of a ContentRequirement for a worker thread."""
    def __init__(self, requirement):
        self.id, self.name = requirement.id, requirement.name
        self.check_type, self.pattern = requirement.check_type, requirement.pattern


def _requirements_of(website: Website) -> list:
    return [_Requirement(r) for r in website.requirements if r.enabled]


def check_website(website: Website, now: datetime | None = None) -> WebsiteHealth:
    """Run one health check now and commit it."""
    now = now or _utcnow()
    found = probe_website(website.url, _requirements_of(website))
    health = record_health(website, found, now)
    db.session.commit()
    return health


def due_websites(now: datetime) -> list:
    """Websites (not retired) whose last check is older than health_check_minutes."""
    interval = timedelta(minutes=_int_setting('health_check_minutes', 5))
    websites = (db.session.query(Website).outerjoin(WebsiteHealth, WebsiteHealth.website_id == Website.id)
                .filter(Website.lifecycle_status != 'retired')
                .filter((WebsiteHealth.checked_at.is_(None)) | (WebsiteHealth.checked_at <= now - interval))
                .order_by(Website.id).all())
    return websites


def run_health_checks(now: datetime | None = None) -> dict:
    """Check every website that is due, WORKERS at a time, then drop uptime rows older
    than health_history_days. Nothing runs while health_checks_enabled is false."""
    if (Settings.get('health_checks_enabled') or '').lower() != 'true':
        return {'checked': 0, 'pruned': 0}
    now = now or _utcnow()
    websites = due_websites(now)
    jobs = [(website, website.url, _requirements_of(website)) for website in websites]
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        results = list(pool.map(lambda job: probe_website(job[1], job[2]), jobs))
    for (website, _, _), found in zip(jobs, results):
        try:
            record_health(website, found, now)
            db.session.commit()
        except Exception as e:
            log_message(f"Could not store the health check of {website.url}: {e}", 'error')
            db.session.rollback()
    cutoff = now - timedelta(days=_int_setting('health_history_days', 1))
    pruned = db.session.query(HealthCheck).filter(HealthCheck.checked_at < cutoff).delete(synchronize_session=False)
    db.session.commit()
    return {'checked': len(jobs), 'pruned': pruned}


# --- reading -------------------------------------------------------------------------------------


def uptime(website_id: int, now: datetime | None = None) -> dict:
    """Share of checks that found the website up over the last day, week and 30 days
    (None when there were no checks in that window), and the checks behind them."""
    now = now or _utcnow()
    rows = (db.session.query(HealthCheck.checked_at, HealthCheck.up)
            .filter(HealthCheck.website_id == website_id, HealthCheck.checked_at >= now - timedelta(days=30)).all())
    out = {}
    for key, days in (('day', 1), ('week', 7), ('month', 30)):
        window = [up for checked_at, up in rows if checked_at >= now - timedelta(days=days)]
        out[key] = round(100 * sum(1 for up in window if up) / len(window), 2) if window else None
    out['checks'] = len(rows)
    return out


def health_summary(website: Website, now: datetime | None = None, history: int = 48) -> dict:
    """The website's latest health, uptime and recent checks for the API."""
    now = now or _utcnow()
    health = db.session.get(WebsiteHealth, website.id)
    recent = (db.session.query(HealthCheck).filter_by(website_id=website.id)
              .order_by(HealthCheck.checked_at.desc()).limit(history).all())
    warn_days = _int_setting('tls_warning_days', 1)
    data = health.to_dict() if health else None
    if data and health.tls_expires_at:
        data['tls_days_left'] = (health.tls_expires_at - now).days
        data['tls_expiring'] = health.tls_expires_at - now <= timedelta(days=warn_days)
    return {
        'health': data,
        'uptime': uptime(website.id, now),
        'recent': [check.to_dict() for check in reversed(recent)],
        'requirements': [{'id': r.id, 'name': r.name} for r in website.requirements],
        'security_headers': list(SECURITY_HEADERS),
    }

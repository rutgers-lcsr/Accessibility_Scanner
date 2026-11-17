"""Crawl inventories: stale content and mixed content per page, media and third-party
hosts per website (models.inventory), and the vendor register they are matched against.

During a crawl, update_page_content runs as each page's report is stored and
collect_page_inventory gathers media and third-party hosts in memory; after the crawl,
sync_media and sync_third_parties bring the website's rows in line, as for documents
and links.
"""
import hashlib
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

from sqlalchemy import func

from models import db
from models.inventory import MAX_URL_LENGTH, MediaItem, MediaSource, ThirdPartyHost, Vendor, match_vendor
from models.settings import Settings
from models.website import Site, Site_Website_Assoc, Website

THIRD_PARTY_KINDS = ('script', 'iframe', 'stylesheet', 'form')
PAGES_KEPT = 10


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def stale_after_days() -> int:
    try:
        return max(1, int(Settings.get('stale_after_days')))
    except (TypeError, ValueError):
        return 365


# --- per page ------------------------------------------------------------------------------


def content_hash(text: str | None) -> str | None:
    """SHA-1 of the text with whitespace collapsed, or None for no text."""
    if not text:
        return None
    return hashlib.sha1(re.sub(r'\s+', ' ', text).strip().encode('utf-8', 'replace')).hexdigest()


def parse_http_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def update_page_content(site: Site, report: dict, now: datetime | None = None) -> None:
    """Record what this scan saw of the page's content (not committed).

    content_changed_at moves to now when the main text's hash differs from the last
    scan's. On the first scan it starts at the Last-Modified date when the server sends
    one, else now; a later Last-Modified moves it forward too.
    """
    now = now or _utcnow()
    digest = content_hash(report.get('content_text'))
    modified = parse_http_date(report.get('last_modified'))
    if modified and modified > now:
        modified = now
    if digest is not None:
        if site.content_hash is None:
            site.content_changed_at = modified or now
        elif site.content_hash != digest:
            site.content_changed_at = now
        site.content_hash = digest
    if modified and (site.content_changed_at is None or modified > site.content_changed_at):
        site.content_changed_at = modified
    site.last_modified = modified
    site.mixed_content = report.get('mixed_content') or []


# --- collection during the crawl -------------------------------------------------------------


def collect_page_inventory(media: dict, third_parties: dict, page_url: str, report: dict) -> None:
    """Add one page's media and third-party hosts to the crawl-wide maps:
    ``media`` is ``{url: {'kind', 'provider', 'captions', 'audio_description', 'pages'}}``
    and ``third_parties`` ``{host: {'kinds', 'example_url', 'pages'}}``."""
    for item in report.get('media') or []:
        url = (item.get('url') or '')[:MAX_URL_LENGTH]
        if not url:
            continue
        entry = media.setdefault(url, {'kind': item.get('kind') or 'embed', 'provider': item.get('provider'),
                                        'captions': item.get('captions') or 'unknown',
                                        'audio_description': bool(item.get('audio_description')), 'pages': set()})
        # One copy with captions is enough for the video to have them.
        if item.get('captions') == 'present':
            entry['captions'] = 'present'
        entry['audio_description'] = entry['audio_description'] or bool(item.get('audio_description'))
        entry['pages'].add(page_url)
    for item in report.get('third_party') or []:
        host = (item.get('host') or '').lower()[:255]
        if not host:
            continue
        entry = third_parties.setdefault(host, {'kinds': set(), 'example_url': item.get('url'), 'pages': set()})
        if item.get('kind') in THIRD_PARTY_KINDS:
            entry['kinds'].add(item['kind'])
        entry['pages'].add(page_url)


# --- after the crawl ---------------------------------------------------------------------------


def sync_media(website_id: int, found: dict, now: datetime | None = None) -> dict:
    """Bring the website's media in line with the crawl: new items are added, known ones
    keep any verdict a person gave, items no longer on any crawled page are removed."""
    now = now or _utcnow()
    existing = {item.url.lower(): item for item in db.session.query(MediaItem).filter_by(website_id=website_id).all()}
    page_urls = {url for info in found.values() for url in info['pages']}
    sites = {site.url: site for site in db.session.query(Site).filter(Site.url.in_(list(page_urls))).all()} if page_urls else {}
    result = {'new': 0, 'updated': 0, 'removed': 0}
    seen = set()
    for url, info in found.items():
        key = url.lower()
        if key in seen:
            continue
        seen.add(key)
        item = existing.get(key)
        if item is None:
            item = MediaItem(website_id=website_id, url=url, first_seen=now)
            db.session.add(item)
            result['new'] += 1
        else:
            result['updated'] += 1
        item.kind = info['kind']
        item.provider = info['provider']
        item.captions = info['captions']
        item.audio_description = info['audio_description']
        item.last_seen = now
        item.pages = [sites[page] for page in sorted(info['pages']) if page in sites]
    for key, item in existing.items():
        if key not in seen:
            db.session.delete(item)
            result['removed'] += 1
    db.session.commit()
    return result


def sync_third_parties(website_id: int, found: dict, now: datetime | None = None) -> dict:
    """Bring the website's third-party hosts in line with the crawl (like sync_media)."""
    now = now or _utcnow()
    website = db.session.get(Website, website_id)
    own_host = (website.url.split('//', 1)[-1].split('/', 1)[0].lower()) if website else ''
    existing = {row.host: row for row in db.session.query(ThirdPartyHost).filter_by(website_id=website_id).all()}
    result = {'new': 0, 'updated': 0, 'removed': 0}
    for host, info in found.items():
        if host == own_host:
            continue
        row = existing.get(host)
        if row is None:
            row = ThirdPartyHost(website_id=website_id, host=host, first_seen=now)
            db.session.add(row)
            result['new'] += 1
        else:
            result['updated'] += 1
        row.kinds = ','.join(sorted(info['kinds']))
        row.example_url = (info.get('example_url') or '')[:MAX_URL_LENGTH] or None
        row.page_count = len(info['pages'])
        row.pages = sorted(info['pages'])[:PAGES_KEPT]
        row.last_seen = now
    for host, row in existing.items():
        if host not in found or host == own_host:
            db.session.delete(row)
            result['removed'] += 1
    db.session.commit()
    return result


# --- reading -------------------------------------------------------------------------------------


def media_counts(website_ids: list) -> dict:
    """``{website_id: {'total', 'missing', 'unknown'}}`` by caption status (a person's
    verdict wins over the crawl's)."""
    if not website_ids:
        return {}
    rows = (db.session.query(MediaItem.website_id, MediaItem.captions, MediaItem.caption_override, func.count())
            .filter(MediaItem.website_id.in_(website_ids))
            .group_by(MediaItem.website_id, MediaItem.captions, MediaItem.caption_override).all())
    out = {website_id: {'total': 0, 'missing': 0, 'unknown': 0} for website_id in website_ids}
    for website_id, captions, override, count in rows:
        status = 'present' if override == 'verified' else 'missing' if override == 'missing' else captions
        out[website_id]['total'] += count
        if status in ('missing', 'unknown'):
            out[website_id][status] += count
    return out


def page_content_counts(website_ids: list, now: datetime | None = None) -> dict:
    """``{website_id: {'stale_pages', 'mixed_content_pages', 'last_change'}}``."""
    if not website_ids:
        return {}
    now = now or _utcnow()
    cutoff = now - timedelta(days=stale_after_days())
    rows = (db.session.query(Site_Website_Assoc.c.website_id, Site.content_changed_at, Site.mixed_content)
            .join(Site, Site.id == Site_Website_Assoc.c.site_id)
            .filter(Site_Website_Assoc.c.website_id.in_(website_ids)).all())
    out = {website_id: {'stale_pages': 0, 'mixed_content_pages': 0, 'last_change': None} for website_id in website_ids}
    for website_id, changed_at, mixed in rows:
        entry = out[website_id]
        if changed_at is not None:
            if changed_at < cutoff:
                entry['stale_pages'] += 1
            if entry['last_change'] is None or changed_at > entry['last_change']:
                entry['last_change'] = changed_at
        if mixed:
            entry['mixed_content_pages'] += 1
    return out


def third_party_rows(website_id: int) -> list:
    """The website's third-party hosts, each with its matching vendor, unmatched ones first."""
    vendors = db.session.query(Vendor).all()
    rows = db.session.query(ThirdPartyHost).filter_by(website_id=website_id).order_by(ThirdPartyHost.host).all()
    out = [row.to_dict(match_vendor(row.host, vendors)) for row in rows]
    out.sort(key=lambda r: (r['vendor'] is not None, -r['page_count'], r['host']))
    return out


def unassigned_hosts() -> list:
    """Third-party hosts seen on any website that match no vendor, most used first:
    ``[{'host', 'websites', 'pages', 'kinds'}]``."""
    vendors = db.session.query(Vendor).all()
    by_host: dict = {}
    for row in db.session.query(ThirdPartyHost).all():
        if match_vendor(row.host, vendors):
            continue
        entry = by_host.setdefault(row.host, {'host': row.host, 'websites': 0, 'pages': 0, 'kinds': set()})
        entry['websites'] += 1
        entry['pages'] += row.page_count
        entry['kinds'].update(k for k in (row.kinds or '').split(',') if k)
    out = [{**entry, 'kinds': sorted(entry['kinds'])} for entry in by_host.values()]
    out.sort(key=lambda e: (-e['websites'], -e['pages'], e['host']))
    return out


def vendor_usage() -> dict:
    """``{vendor_id: number of websites using it}``."""
    vendors = db.session.query(Vendor).all()
    usage: dict = {vendor.id: set() for vendor in vendors}
    for row in db.session.query(ThirdPartyHost.website_id, ThirdPartyHost.host).all():
        vendor = match_vendor(row.host, vendors)
        if vendor:
            usage[vendor.id].add(row.website_id)
    return {vendor_id: len(websites) for vendor_id, websites in usage.items()}

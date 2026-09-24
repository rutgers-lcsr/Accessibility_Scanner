"""Owner digests and reminders (README, "Emails").

One email per person covering every website they administer or belong to, sent by the
daily task only when something changed for them since they were last emailed, or when a
reminder is due. The change baseline is the person's own ``User.last_digest_at``;
``Website.last_notified`` keeps being stamped for the Owners page and its CSV.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import joinedload, selectinload

from config import CLIENT_URL
from models import db
from models.notifications import NotificationOptOut, WebsiteView
from models.settings import Settings
from models.user import User
from models.website import Website
from services.findings import findings_since, last_activity_at
from services.guides import available_guides
from services.overview import IMPACT_ORDER, _violations_total, build_overview, effective_counts, iso, latest_reports, top_rules
from utils.urls import get_netloc

RULE_TAB = 'fix'           # the website page's Fix first tab
FIX_FIRST = 3              # rules in the "fix these first" list
_TOP_RULES_PER_WEBSITE = 20
_FIX_FIRST_MAX_REPORTS = 1500
DIGEST_MIN_INTERVAL = timedelta(hours=20)  # one digest a day, however often the task runs


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def rule_link(website_id: int, rule_id: str) -> str:
    return f"{CLIENT_URL}/websites/{website_id}?tab={RULE_TAB}&rule={rule_id}"


def guide_link(rule: dict, guides=None) -> str:
    """Our fix guide when there is one, else the rule's own help page."""
    guides = available_guides() if guides is None else guides
    if rule['id'] in guides:
        return f"{CLIENT_URL}/help/fix/{rule['id']}"
    return rule.get('help_url') or f"{CLIENT_URL}/help/fix"


def member_websites(user: User) -> list:
    """Every website the person administers or belongs to, by URL."""
    websites = {website.id: website for website in user.admin_websites}
    websites.update({website.id: website for website in user.viewable_websites})
    return sorted(websites.values(), key=lambda website: website.url)


def owner_websites(user: User) -> list:
    """The websites this person is emailed about: theirs, email switched on, not opted out."""
    opted_out = {
        row.website_id for row in
        db.session.query(NotificationOptOut.website_id).filter_by(user_id=user.id).all()
    }
    return [website for website in member_websites(user) if website.should_email and website.id not in opted_out]


def digest_users() -> list:
    """Active people with an address who are emailed about at least one website."""
    users = (
        db.session.query(User)
        .options(selectinload(User.admin_websites), selectinload(User.viewable_websites))
        .filter(User.is_active == True)
        .order_by(User.username)
        .all()
    )
    return [user for user in users if user.email and 'localhost' not in user.email and owner_websites(user)]


def reminder_settings() -> dict:
    def integer(key, default):
        try:
            return max(1, int(Settings.get(key)))
        except (TypeError, ValueError):
            return default

    return {
        'enabled': (Settings.get('owner_digest_enabled') or 'true').lower() == 'true',
        'after_days': integer('reminder_after_days', 30),
        'escalate_days': integer('escalate_after_days', 60),
        'email': (Settings.get('escalation_email') or '').strip(),
    }


def _fix_first(websites, overview, guides) -> list:
    """The rules across the person's websites that clear the most pages, from the latest
    report of every page (worst websites first, capped so a huge owner stays cheap)."""
    latest = overview['latest_by_site']
    sites_of = overview['sites_of']
    row_of = {row['id']: row for row in overview['websites']}
    merged = {}
    budget = _FIX_FIRST_MAX_REPORTS
    for website in sorted(websites, key=lambda w: -row_of[w.id]['violations']['total']):
        report_ids = [latest[site_id].id for site_id in sites_of.get(website.id, ()) if site_id in latest]
        report_ids = report_ids[:budget]
        budget -= len(report_ids)
        if not report_ids:
            continue
        for rule in top_rules(report_ids, _TOP_RULES_PER_WEBSITE):
            entry = merged.setdefault(rule['id'], {**rule, 'pages': 0, 'occurrences': 0, 'website_id': None, 'website_pages': 0})
            entry['pages'] += rule['pages']
            entry['occurrences'] += rule['occurrences']
            if rule['pages'] > entry['website_pages']:
                entry['website_pages'] = rule['pages']
                entry['website_id'] = website.id
                entry['website_host'] = get_netloc(website.url)
        if budget <= 0:
            break
    ranked = sorted(merged.values(), key=lambda r: (-r['pages'], IMPACT_ORDER.get(r['impact'], len(IMPACT_ORDER)), -r['occurrences']))
    return [{
        'rule_id': rule['id'], 'help': rule['help'], 'help_url': rule['help_url'], 'impact': rule['impact'],
        'pages': rule['pages'], 'occurrences': rule['occurrences'],
        'website_id': rule['website_id'], 'website_host': rule['website_host'],
        'link': rule_link(rule['website_id'], rule['id']), 'guide': guide_link(rule, guides),
    } for rule in ranked[:FIX_FIRST]]


def build_owner_digest(user, websites, since, now=None, guides=None, overview=None, escalation_email: str = '') -> dict:
    """Plain data for one person's digest: their websites now and at ``since`` (when they
    were last emailed), what got fixed and what is new since then, the fixes that clear
    the most pages, and how engaged they have been."""
    now = now or _utcnow()
    since = since.replace(tzinfo=None) if since and since.tzinfo else since
    website_ids = [website.id for website in websites]
    overview = overview or build_overview(websites, top=0)
    row_of = {row['id']: row for row in overview['websites']}
    sites_of = overview['sites_of']
    latest = overview['latest_by_site']
    then = latest_reports(website_ids, before=since) if since else {}
    counts = findings_since(website_ids, since)
    views = WebsiteView.by_website(website_ids)
    guides = available_guides() if guides is None else guides

    rows = []
    for website in websites:
        row = row_of[website.id]
        site_ids = sites_of.get(website.id, set())
        previous = _violations_total({site_id: then[site_id] for site_id in site_ids if site_id in then}) if since else None
        moved = counts.get(website.id, {'fixed': 0, 'triaged': 0, 'new': 0})
        scanned_since = bool(website.last_scanned and (since is None or website.last_scanned > since))
        failing = website.last_scan_status in ('failed', 'unreachable')
        violations = row['violations']
        changed = scanned_since and (previous is None or previous != violations['total'] or moved['fixed'] > 0 or moved['new'] > 0 or failing)
        pages_with_issues = sum(
            1 for site_id in site_ids
            if site_id in latest and effective_counts(latest[site_id].report_counts, latest[site_id].suppressed_counts)['violations']['total'] > 0
        )
        viewed = views.get(website.id, {}).get(user.id) if user else None
        escalated = bool(website.escalated_at)
        rows.append({
            'id': website.id, 'url': website.url, 'host': get_netloc(website.url),
            'last_scanned': iso(website.last_scanned), 'last_scan_status': website.last_scan_status,
            'last_scan_error': website.last_scan_error, 'pages': row['pages'], 'pages_audited': row['pages_audited'],
            'pages_with_issues': pages_with_issues, 'violations': violations, 'previous_violations': previous,
            'new_since': moved['new'], 'fixed_since': moved['fixed'], 'triaged_since': moved['triaged'],
            'viewed_at': iso(viewed), 'scanned_since': scanned_since, 'changed': changed, 'failing': failing,
            'escalated': escalated,
            'show': changed or failing or violations['critical'] > 0 or violations['serious'] > 0 or since is None,
        })

    totals = {
        'violations': sum(r['violations']['total'] for r in rows),
        'critical_serious': sum(r['violations']['critical'] + r['violations']['serious'] for r in rows),
        'previous': sum(r['previous_violations'] for r in rows if r['previous_violations'] is not None) if any(r['previous_violations'] is not None for r in rows) else None,
        'pages_with_issues': sum(r['pages_with_issues'] for r in rows),
        'fixed_since': sum(r['fixed_since'] for r in rows),
        'new_since': sum(r['new_since'] for r in rows),
        'triaged_since': sum(r['triaged_since'] for r in rows),
    }
    seen = [views.get(w.id, {}).get(user.id) for w in websites] if user else []
    last_viewed = max((when for when in seen if when is not None), default=None)
    if totals['fixed_since'] > 0:
        engagement = 'fixed'
    elif last_viewed is None:
        engagement = 'never_opened'
    elif since and last_viewed < since:
        engagement = 'not_since_last_email'
    else:
        engagement = 'looked_no_change'

    return {
        'since': iso(since), 'generated_at': iso(now),
        'user': {'username': user.username if user else None, 'last_login': iso(user.last_login) if user else None,
                 'last_viewed': iso(last_viewed)},
        'websites': rows, 'hidden_websites': sum(1 for r in rows if not r['show']),
        'totals': totals,
        'fix_first': _fix_first(websites, overview, guides),
        'failing': [r for r in rows if r['failing']],
        'engagement': engagement,
        'escalation_email': escalation_email,
    }


def digest_changed(digest: dict) -> bool:
    """Whether the person has anything new to hear: the first digest with any audited page,
    or a website scanned since the last one whose numbers moved or whose scan failed."""
    if digest['since'] is None:
        return any(row['pages_audited'] > 0 or row['failing'] for row in digest['websites'])
    return any(row['changed'] for row in digest['websites'])


def reminder_due(website: Website, violations: dict, activity_at, settings: dict, now: datetime):
    """'reminder', 'escalation' or None, updating the website's streak as a side effect:
    the streak starts when the website's people were last emailed and resets on activity
    (a verdict, or something the scanner saw fixed). One reminder per period; escalation
    once the second period has passed and an address is configured."""
    needs = violations['critical'] > 0 or violations['serious'] > 0
    anchor = website.attention_since or website.last_notified
    if not needs or (activity_at and anchor and activity_at > anchor):
        website.attention_since = None
        website.last_reminded_at = None
        website.reminder_count = 0
        website.escalated_at = None
        return None
    if website.last_notified is None:
        return None  # the digest goes first
    if website.attention_since is None:
        website.attention_since = website.last_notified
    period = timedelta(days=settings['after_days'])
    if now - website.attention_since < period:
        return None
    if website.last_reminded_at and now - website.last_reminded_at < period:
        return None
    if settings['email'] and (website.escalated_at or now - website.attention_since >= timedelta(days=settings['escalate_days'])):
        return 'escalation'
    return 'reminder'


def run_owner_digests(now=None, dry_run: bool = False, user_ids=None) -> dict:
    """Send every digest and reminder that is due. ``user_ids`` picks people by hand and
    sends to them even when nothing changed. Returns counts and, for a dry run, one line
    per person saying what they would get. State is committed per person after a
    successful send, so a crash mid-run cannot email anyone twice."""
    from mail.emails import OwnerDigestEmail  # local import: mail imports services

    now = now or _utcnow()
    settings = reminder_settings()
    result = {'users': 0, 'sent': 0, 'reminders': 0, 'escalations': 0, 'skipped': 0, 'details': []}

    websites = db.session.query(Website).options(joinedload(Website.admin)).order_by(Website.url).all()
    if not websites:
        return result
    overview = build_overview(websites, top=0)
    row_of = {row['id']: row for row in overview['websites']}
    activity = last_activity_at([website.id for website in websites])
    due = {}
    for website in websites:
        level = reminder_due(website, row_of[website.id]['violations'], activity.get(website.id), settings, now)
        if level:
            due[website.id] = level
    if not dry_run:
        db.session.commit()  # streak resets and starts, whoever gets emailed
    guides = available_guides()

    if user_ids is None:
        users = digest_users()
    else:
        users = db.session.query(User).filter(User.id.in_(list(user_ids))).all()

    for user in users:
        result['users'] += 1
        if user_ids is None and user.last_digest_at and now - user.last_digest_at < DIGEST_MIN_INTERVAL:
            result['skipped'] += 1
            continue
        mine = owner_websites(user)
        if not mine:
            result['skipped'] += 1
            continue
        digest = build_owner_digest(user, mine, user.last_digest_at, now, guides, escalation_email=settings['email'])
        due_here = {website.id: due[website.id] for website in mine if website.id in due}
        monthly = digest['totals']['critical_serious'] > 0 and (
            user.last_digest_at is None or now - user.last_digest_at >= timedelta(days=settings['after_days']))
        changed = digest_changed(digest)
        if not (changed or due_here or monthly or user_ids is not None):
            result['skipped'] += 1
            continue
        if 'escalation' in due_here.values():
            tone = 'escalation'
        elif due_here:
            tone = 'reminder'
        elif user.last_digest_at is None:
            tone = 'first'
        elif changed:
            tone = 'update'
        else:
            tone = 'no_change'
        for row in digest['websites']:
            row['escalated'] = due_here.get(row['id']) == 'escalation'
            row['show'] = row['show'] or row['id'] in due_here
        digest['hidden_websites'] = sum(1 for row in digest['websites'] if not row['show'])
        cc = None
        if tone == 'escalation' and settings['email'] and any(
                due_here.get(website.id) == 'escalation' and website.admin_id == user.id for website in mine):
            cc = [settings['email']]
        email = OwnerDigestEmail(user, digest, tone=tone, cc=cc)
        if dry_run:
            result['details'].append(f"{user.username} <{user.email}>: {tone}: {email.subject()}"
                                     + (f" (cc {settings['email']})" if cc else ''))
            result['sent'] += 1
            continue
        if not email.send():
            result['skipped'] += 1
            continue
        result['sent'] += 1
        user.last_digest_at = now
        for website in mine:
            website.last_notified = now
            level = due_here.get(website.id)
            if level and website.last_reminded_at != now:
                website.last_reminded_at = now
                website.reminder_count = (website.reminder_count or 0) + 1
                result['reminders' if level == 'reminder' else 'escalations'] += 1
                if level == 'escalation' and not website.escalated_at:
                    website.escalated_at = now
        db.session.commit()
    if dry_run:
        db.session.rollback()
    return result


def send_website_digest(website: Website, email: str | None = None) -> int:
    """A site admin's "send now": this website's digest to each of its people (and to an
    extra address, without an unsubscribe link). Stamps the website's last_notified, not
    anyone's last_digest_at, so the next daily digest still covers their other websites."""
    from mail.emails import OwnerDigestEmail  # local import: mail imports services

    now = _utcnow()
    overview = build_overview([website], top=0)
    guides = available_guides()
    messages = 0
    for user in website.get_recipients():
        if not user.email:
            continue
        digest = build_owner_digest(user, [website], user.last_digest_at, now, guides, overview)
        tone = 'first' if user.last_digest_at is None else 'update'
        if OwnerDigestEmail(user, digest, tone=tone).send():
            messages += 1
    if email:
        digest = build_owner_digest(None, [website], website.last_notified, now, guides, overview)
        if OwnerDigestEmail(None, digest, tone='update', address=email).send():
            messages += 1
    if messages:
        website.last_notified = now
        db.session.commit()
    return messages

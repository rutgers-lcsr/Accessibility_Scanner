"""Findings: one failing element per page, tracked across scans.

Identity is ``sha1(rule_id + "\\n" + selector)`` with the selector normalised from
axe's ``target``. When a page changes, positional selectors (``:nth-child``) shift;
an unmatched node whose HTML matches exactly one unmatched finding takes over that
finding, so the history survives the shift without ever guessing among identical
elements.

``report_counts.violations`` counts *rules* per page, so ``suppressed_counts`` counts
the rules whose current findings are all suppressed (false positive or accepted).
"""
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import and_, case, func, or_, true

from models import db
from models.finding import FINDING_STATUSES, Finding, SUPPRESSED_STATUSES
from models.report import Report
from models.website import Site, Site_Website_Assoc
from services.history import effective_counts, sum_counts

IMPACT_KEYS = ('critical', 'serious', 'moderate', 'minor')


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _naive(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


# --- identity -------------------------------------------------------------------------


def normalise_selector(target) -> str:
    """axe's ``target`` is a list of selectors, nested for shadow DOM; one canonical string."""
    parts = []

    def walk(value):
        if isinstance(value, (list, tuple)):
            for item in value:
                walk(item)
        elif value is not None:
            text = str(value).strip()
            if text:
                parts.append(text)

    walk(target)
    return ' >>> '.join(parts)


def normalise_html(html) -> str:
    return ' '.join(str(html or '').split())[:2000]


def normalise_summary(text) -> str | None:
    """axe's failureSummary with its whitespace collapsed, capped; None when empty."""
    summary = ' '.join(str(text or '').split())[:1000]
    return summary or None


def fingerprint(rule_id: str, selector: str) -> str:
    return hashlib.sha1(f"{rule_id}\n{selector}".encode()).hexdigest()


def html_key(rule_id: str, html) -> str:
    return hashlib.sha1(f"{rule_id}\nhtml:{normalise_html(html)}".encode()).hexdigest()


# --- sync at store time ----------------------------------------------------------------


@dataclass
class SyncResult:
    new: int = 0
    reopened: int = 0
    closed: int = 0
    unchanged: int = 0


def _nodes_of(violations):
    """``(fingerprint, rule, node, selector)`` per node, de-duplicated within the report."""
    seen = set()
    nodes = []
    for rule in violations or []:
        rule_id = rule.get('id')
        if not rule_id:
            continue
        for node in rule.get('nodes') or []:
            selector = normalise_selector(node.get('target'))
            fp = fingerprint(rule_id, selector) if selector else html_key(rule_id, node.get('html'))
            if fp in seen:
                continue
            seen.add(fp)
            nodes.append((fp, rule, node, selector))
    return nodes


def _refresh(finding: Finding, rule, node, selector, report_id, report_ts, now, result: SyncResult):
    finding.last_seen = report_ts
    finding.last_report_id = report_id
    finding.impact = rule.get('impact')
    finding.help = (rule.get('help') or '')[:500]
    finding.help_url = (rule.get('helpUrl') or '')[:500]
    finding.selector = selector
    finding.html = normalise_html(node.get('html'))
    finding.failure_summary = normalise_summary(node.get('failureSummary'))
    if finding.status == 'fixed':
        # It came back: reopen, keeping any note. Suppressed statuses are sticky.
        finding.status = 'open'
        finding.status_by = None
        finding.status_at = now
        result.reopened += 1
    else:
        result.unchanged += 1


def sync_report_findings(site_id: int, report_id: int, report_ts: datetime, violations, now: datetime | None = None) -> SyncResult:
    """Bring the page's findings in line with a report just stored for it. No commit."""
    now = now or _utcnow()
    report_ts = _naive(report_ts) or now
    existing = {f.fingerprint: f for f in db.session.query(Finding).filter_by(site_id=site_id).all()}
    result = SyncResult()
    matched = set()
    unmatched_nodes = []

    for fp, rule, node, selector in _nodes_of(violations):
        finding = existing.get(fp)
        if finding is not None:
            matched.add(finding)
            _refresh(finding, rule, node, selector, report_id, report_ts, now, result)
        else:
            unmatched_nodes.append((fp, rule, node, selector))

    if unmatched_nodes:
        # Secondary match: the same HTML under a new selector, only when unambiguous.
        findings_by_key = {}
        for finding in existing.values():
            if finding not in matched:
                findings_by_key.setdefault(html_key(finding.rule_id, finding.html), []).append(finding)
        nodes_by_key = {}
        for entry in unmatched_nodes:
            nodes_by_key.setdefault(html_key(entry[1].get('id'), entry[2].get('html')), []).append(entry)
        for key, node_group in nodes_by_key.items():
            finding_group = findings_by_key.get(key, [])
            if len(node_group) == 1 and len(finding_group) == 1:
                fp, rule, node, selector = node_group[0]
                finding = finding_group[0]
                finding.fingerprint = fp
                matched.add(finding)
                _refresh(finding, rule, node, selector, report_id, report_ts, now, result)
                node_group.clear()
        for fp, rule, node, selector in (entry for group in nodes_by_key.values() for entry in group):
            db.session.add(Finding(
                site_id=site_id, rule_id=rule.get('id'), fingerprint=fp,
                impact=rule.get('impact'), help=(rule.get('help') or '')[:500],
                help_url=(rule.get('helpUrl') or '')[:500], selector=selector,
                html=normalise_html(node.get('html')),
                failure_summary=normalise_summary(node.get('failureSummary')),
                first_seen=report_ts, last_seen=report_ts,
                last_report_id=report_id, status='open',
            ))
            result.new += 1

    for finding in existing.values():
        if finding not in matched and finding.status == 'open':
            finding.status = 'fixed'
            finding.status_by = None
            finding.status_at = now
            result.closed += 1
    return result


# --- suppression snapshot -------------------------------------------------------------


def suppressed_counts_for(site_id: int, report_id: int) -> dict:
    """Rules whose findings in this report are all suppressed, bucketed by impact."""
    rows = (
        db.session.query(Finding.rule_id, Finding.impact, Finding.status)
        .filter_by(site_id=site_id, last_report_id=report_id)
        .all()
    )
    per_rule = {}
    for rule_id, impact, status in rows:
        entry = per_rule.setdefault(rule_id, {'impact': impact, 'suppressed': True})
        if status not in SUPPRESSED_STATUSES:
            entry['suppressed'] = False
    counts = {'total': 0, **{key: 0 for key in IMPACT_KEYS}}
    for entry in per_rule.values():
        if entry['suppressed']:
            counts['total'] += 1
            if entry['impact'] in counts:
                counts[entry['impact']] += 1
    return counts


def refresh_suppressed_counts(site_id: int, report_id: int) -> dict:
    """Rewrite the report's snapshot without loading the row (no report JSON, no photo)."""
    counts = suppressed_counts_for(site_id, report_id)
    db.session.query(Report).filter(Report.id == report_id).update(
        {'suppressed_counts': counts}, synchronize_session=False
    )
    return counts


def suppressed_fingerprints(site_ids) -> set:
    """``{(site_id, fingerprint)}`` of suppressed findings on the given pages."""
    if not site_ids:
        return set()
    rows = (
        db.session.query(Finding.site_id, Finding.fingerprint)
        .filter(Finding.site_id.in_(list(site_ids)), Finding.status.in_(SUPPRESSED_STATUSES))
        .all()
    )
    return {(site_id, fp) for site_id, fp in rows}


def latest_report_ids(site_ids) -> dict:
    """``{site_id: report_id}`` of each page's newest report."""
    if not site_ids:
        return {}
    latest_ts = (
        db.session.query(Report.site_id, func.max(Report.timestamp).label('ts'))
        .filter(Report.site_id.in_(list(site_ids)))
        .group_by(Report.site_id)
        .subquery()
    )
    rows = (
        db.session.query(Report.id, Report.site_id)
        .join(latest_ts, (latest_ts.c.site_id == Report.site_id) & (latest_ts.c.ts == Report.timestamp))
        .all()
    )
    latest = {}
    for report_id, site_id in rows:
        latest[site_id] = max(report_id, latest.get(site_id, 0))
    return latest


# --- triage ------------------------------------------------------------------------------


TRIAGED_STATUSES = ('fixed',) + SUPPRESSED_STATUSES


def triage_activity(website_ids) -> dict:
    """``{website_id: {'triaged': n, 'last_triage': datetime | None}}``: the findings a
    person (``status_by`` set; the scanner leaves it NULL) marked fixed, false positive
    or accepted on the website's pages, and when the latest verdict was given."""
    if not website_ids:
        return {}
    rows = (
        db.session.query(Site_Website_Assoc.c.website_id, func.count(Finding.id), func.max(Finding.status_at))
        .select_from(Site_Website_Assoc)
        .join(Finding, Finding.site_id == Site_Website_Assoc.c.site_id)
        .filter(
            Site_Website_Assoc.c.website_id.in_(list(website_ids)),
            Finding.status_by.isnot(None),
            Finding.status.in_(TRIAGED_STATUSES),
        )
        .group_by(Site_Website_Assoc.c.website_id)
        .all()
    )
    return {website_id: {'triaged': count, 'last_triage': last} for website_id, count, last in rows}


def set_finding_status(finding: Finding, status: str, note: str | None, user_id: int | None) -> None:
    """Record a person's verdict on a finding and refresh its report's snapshot. No commit."""
    if status not in FINDING_STATUSES:
        raise ValueError(f"status must be one of {', '.join(FINDING_STATUSES)}")
    finding.status = status
    finding.status_by = user_id
    finding.status_at = _utcnow()
    if note is not None:
        finding.note = note.strip()[:2000] or None
    if finding.last_report_id is not None:
        db.session.flush()
        refresh_suppressed_counts(finding.site_id, finding.last_report_id)


def bulk_set_status(site_ids, rule_id: str, status: str, note: str | None, user_id: int | None) -> int:
    """Apply a verdict to every current finding of one rule on the given pages."""
    latest = latest_report_ids(site_ids)
    if not latest:
        return 0
    findings = (
        db.session.query(Finding)
        .filter(Finding.rule_id == rule_id, Finding.site_id.in_(list(latest)))
        .all()
    )
    updated = 0
    for finding in findings:
        if finding.last_report_id == latest.get(finding.site_id):
            set_finding_status(finding, status, note, user_id)
            updated += 1
    return updated


def findings_since(website_ids, since: datetime | None) -> dict:
    """``{website_id: {'fixed': n, 'triaged': n, 'new': n}}`` since ``since`` (all time
    when None): findings the scanner closed (status fixed, status_by NULL), verdicts
    people gave (status_by set, TRIAGED_STATUSES), and open findings first seen."""
    if not website_ids:
        return {}
    since = _naive(since)

    def after(column):
        return true() if since is None else column >= since

    scanner_fixed = case((and_(Finding.status == 'fixed', Finding.status_by.is_(None), after(Finding.status_at)), 1), else_=0)
    triaged = case((and_(Finding.status_by.isnot(None), Finding.status.in_(TRIAGED_STATUSES), after(Finding.status_at)), 1), else_=0)
    new = case((and_(Finding.status == 'open', after(Finding.first_seen)), 1), else_=0)
    rows = (
        db.session.query(Site_Website_Assoc.c.website_id, func.sum(scanner_fixed), func.sum(triaged), func.sum(new))
        .select_from(Site_Website_Assoc)
        .join(Finding, Finding.site_id == Site_Website_Assoc.c.site_id)
        .filter(Site_Website_Assoc.c.website_id.in_(list(website_ids)))
        .group_by(Site_Website_Assoc.c.website_id)
        .all()
    )
    return {website_id: {'fixed': int(fixed or 0), 'triaged': int(verdicts or 0), 'new': int(fresh or 0)}
            for website_id, fixed, verdicts, fresh in rows}


def last_activity_at(website_ids) -> dict:
    """``{website_id: datetime | None}``: when a person last acted on the website, that is
    gave a verdict, or something got fixed (the scanner closed a finding). Looking at a
    report is not acting."""
    if not website_ids:
        return {}
    acted = or_(
        and_(Finding.status_by.isnot(None), Finding.status.in_(TRIAGED_STATUSES)),
        and_(Finding.status == 'fixed', Finding.status_by.is_(None)),
    )
    rows = (
        db.session.query(Site_Website_Assoc.c.website_id, func.max(Finding.status_at))
        .select_from(Site_Website_Assoc)
        .join(Finding, Finding.site_id == Site_Website_Assoc.c.site_id)
        .filter(Site_Website_Assoc.c.website_id.in_(list(website_ids)), acted)
        .group_by(Site_Website_Assoc.c.website_id)
        .all()
    )
    return {website_id: last for website_id, last in rows}


def list_findings(site_ids, status: str = 'current', rule_id: str | None = None) -> dict:
    """Findings grouped by rule, then page. ``status``: current (in the page's latest
    report), open, suppressed, fixed or all."""
    if not site_ids:
        return {'count': 0, 'rules': []}
    latest = latest_report_ids(site_ids)
    query = db.session.query(Finding).filter(Finding.site_id.in_(list(site_ids)))
    if rule_id:
        query = query.filter(Finding.rule_id == rule_id)
    if status == 'open':
        query = query.filter(Finding.status == 'open')
    elif status == 'suppressed':
        query = query.filter(Finding.status.in_(SUPPRESSED_STATUSES))
    elif status == 'fixed':
        query = query.filter(Finding.status == 'fixed')
    findings = query.order_by(Finding.rule_id, Finding.site_id, Finding.id).all()
    if status == 'current':
        findings = [f for f in findings if f.last_report_id == latest.get(f.site_id)]

    rules = {}
    for finding in findings:
        rule = rules.setdefault(finding.rule_id, {
            'rule_id': finding.rule_id, 'impact': finding.impact, 'help': finding.help,
            'help_url': finding.help_url,
            'counts': {key: 0 for key in FINDING_STATUSES},
            'pages': {},
        })
        rule['counts'][finding.status] += 1
        page = rule['pages'].setdefault(finding.site_id, {
            'site_id': finding.site_id, 'url': finding.site.url,
            'report_id': latest.get(finding.site_id), 'findings': [],
        })
        page['findings'].append(finding.to_dict())
    for rule in rules.values():
        rule['pages'] = list(rule['pages'].values())
    ordered = sorted(rules.values(), key=lambda r: (IMPACT_KEYS.index(r['impact']) if r['impact'] in IMPACT_KEYS else len(IMPACT_KEYS), r['rule_id']))
    return {'count': len(findings), 'rules': ordered}


def fix_first(site_ids, guide_ids=frozenset()) -> dict:
    """Rules ranked by the pages a fix clears, over the current findings of the given
    pages. A page counts for a rule when it has an open current finding of it
    (suppressed and fixed ones need no fixing); the status counts cover every current
    finding. Reads the finding table and the latest report ids only."""
    site_ids = list(site_ids)
    latest = latest_report_ids(site_ids)
    result = {'pages_total': len(site_ids), 'pages_audited': len(latest), 'open_total': 0,
              'suppressed_rules': 0, 'rules': []}
    if not latest:
        return result
    rows = (
        db.session.query(Finding.id, Finding.site_id, Finding.rule_id, Finding.impact, Finding.help,
                         Finding.help_url, Finding.status, Finding.selector, Finding.html,
                         Finding.failure_summary, Site.url)
        .join(Site, Site.id == Finding.site_id)
        .filter(Finding.site_id.in_(site_ids), Finding.last_report_id.in_(list(latest.values())))
        .order_by(Finding.rule_id, Finding.site_id, Finding.id)
        .all()
    )
    rules, first_open = {}, {}
    for row in rows:
        rule = rules.setdefault(row.rule_id, {
            'rule_id': row.rule_id, 'impact': row.impact, 'help': row.help, 'help_url': row.help_url,
            'counts': {key: 0 for key in FINDING_STATUSES}, 'pages': {},
        })
        rule['counts'][row.status] += 1
        if row.status != 'open':
            continue
        page = rule['pages'].setdefault(row.site_id, {
            'site_id': row.site_id, 'url': row.url, 'report_id': latest[row.site_id], 'count': 0,
        })
        page['count'] += 1
        first_open.setdefault((row.rule_id, row.site_id), row)

    ranked = []
    for rule in rules.values():
        pages = sorted(rule['pages'].values(), key=lambda page: (-page['count'], page['url']))
        if not pages:
            result['suppressed_rules'] += 1
            continue
        example = first_open[(rule['rule_id'], pages[0]['site_id'])]
        elements = sum(page['count'] for page in pages)
        result['open_total'] += elements
        ranked.append({
            **rule,
            'pages': pages,
            'pages_affected': len(pages),
            'pages_cleared_percent': round(100 * len(pages) / len(latest)),
            'elements': elements,
            'example': {
                'finding_id': example.id, 'site_id': example.site_id, 'url': example.url,
                'report_id': latest[example.site_id], 'selector': example.selector,
                'html': example.html, 'failure_summary': example.failure_summary,
            },
            'guide': rule['rule_id'] in guide_ids,
        })
    ranked.sort(key=lambda rule: (
        -rule['pages_affected'],
        IMPACT_KEYS.index(rule['impact']) if rule['impact'] in IMPACT_KEYS else len(IMPACT_KEYS),
        rule['rule_id'],
    ))
    result['rules'] = ranked
    return result


# --- what changed ------------------------------------------------------------------------


def _iso(value: datetime | None) -> str | None:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ") if value else None


def latest_and_previous_reports(site_ids) -> tuple[dict, dict]:
    """``({site_id: latest_row}, {site_id: previous_row})`` with light columns only."""
    if not site_ids:
        return {}, {}
    columns = (Report.id, Report.site_id, Report.url, Report.timestamp, Report.report_counts, Report.suppressed_counts)
    latest_ts = (
        db.session.query(Report.site_id, func.max(Report.timestamp).label('ts'))
        .filter(Report.site_id.in_(list(site_ids)))
        .group_by(Report.site_id)
        .subquery()
    )
    previous_ts = (
        db.session.query(Report.site_id, func.max(Report.timestamp).label('ts'))
        .join(latest_ts, latest_ts.c.site_id == Report.site_id)
        .filter(Report.timestamp < latest_ts.c.ts)
        .group_by(Report.site_id)
        .subquery()
    )

    def newest_per_site(subquery):
        rows = (
            db.session.query(*columns)
            .join(subquery, (subquery.c.site_id == Report.site_id) & (subquery.c.ts == Report.timestamp))
            .all()
        )
        by_site = {}
        for row in rows:
            if row.site_id not in by_site or row.id > by_site[row.site_id].id:
                by_site[row.site_id] = row
        return by_site

    return newest_per_site(latest_ts), newest_per_site(previous_ts)


def _group_by_rule(findings, page_report_id):
    """Findings → rules, most severe and most widespread first, with their pages."""
    rules = {}
    for finding, reopened in findings:
        rule = rules.setdefault(finding.rule_id, {
            'rule_id': finding.rule_id, 'impact': finding.impact, 'help': finding.help,
            'help_url': finding.help_url, 'count': 0, 'pages': {},
        })
        rule['count'] += 1
        page = rule['pages'].setdefault(finding.site_id, {
            'site_id': finding.site_id, 'url': finding.site.url,
            'report_id': page_report_id(finding.site_id), 'count': 0, 'findings': [],
        })
        page['count'] += 1
        page['findings'].append({'id': finding.id, 'selector': finding.selector, 'reopened': reopened})
    ordered = []
    for rule in rules.values():
        rule['pages'] = sorted(rule['pages'].values(), key=lambda p: (-p['count'], p['url']))
        ordered.append(rule)
    ordered.sort(key=lambda r: (IMPACT_KEYS.index(r['impact']) if r['impact'] in IMPACT_KEYS else len(IMPACT_KEYS), -r['count'], r['rule_id']))
    return ordered


def changes_for_sites(site_ids) -> dict:
    """New, fixed and still-open findings between the previous and the latest scan of
    the given pages, plus effective violation totals then and now over the pages that
    have both. ``since`` is None when no page has a previous report."""
    latest, previous = latest_and_previous_reports(site_ids)
    empty_counts = {'total': 0, **{key: 0 for key in IMPACT_KEYS}}
    result = {
        'since': _iso(max((row.timestamp for row in previous.values()), default=None)),
        'until': _iso(max((row.timestamp for row in latest.values()), default=None)),
        'previous': dict(empty_counts), 'current': dict(empty_counts),
        'new': [], 'fixed': [], 'still_open': [],
        'new_count': 0, 'reopened_count': 0, 'fixed_count': 0, 'open_count': 0, 'suppressed_count': 0,
    }
    if not latest:
        result['regression'] = False
        return result

    both = [site_id for site_id in latest if site_id in previous]
    result['previous'] = sum_counts({s: effective_counts(previous[s].report_counts, previous[s].suppressed_counts) for s in both})['violations']
    result['current'] = sum_counts({s: effective_counts(latest[s].report_counts, latest[s].suppressed_counts) for s in both})['violations']

    report_ids = {row.id for row in latest.values()} | {row.id for row in previous.values()}
    findings = (
        db.session.query(Finding)
        .filter(Finding.site_id.in_(list(latest)), Finding.last_report_id.in_(list(report_ids)))
        .all()
    )
    new, fixed, still_open = [], [], []
    for finding in findings:
        latest_row = latest.get(finding.site_id)
        previous_row = previous.get(finding.site_id)
        if latest_row and finding.last_report_id == latest_row.id:
            if finding.status in SUPPRESSED_STATUSES:
                result['suppressed_count'] += 1
            elif finding.status == 'open':
                result['open_count'] += 1
                reopened = (
                    finding.status_by is None and finding.status_at is not None
                    and finding.status_at >= _naive(latest_row.timestamp)
                )
                if finding.first_seen == finding.last_seen:
                    new.append((finding, False))
                elif reopened:
                    new.append((finding, True))
                    result['reopened_count'] += 1
                else:
                    still_open.append((finding, False))
        elif previous_row and finding.last_report_id == previous_row.id and finding.status == 'fixed':
            fixed.append((finding, False))

    result['new_count'] = len(new)
    result['fixed_count'] = len(fixed)
    result['new'] = _group_by_rule(new, lambda site_id: latest[site_id].id)
    result['still_open'] = _group_by_rule(still_open, lambda site_id: latest[site_id].id)
    result['fixed'] = _group_by_rule(fixed, lambda site_id: previous[site_id].id)
    result['regression'] = is_regression(result)
    return result


def is_regression(changes: dict) -> bool:
    """Worse than the previous scan: a new or reopened critical/serious finding, or more
    open violations over the pages present in both scans. Never on a first scan."""
    if not changes.get('since'):
        return False
    if any(rule['impact'] in ('critical', 'serious') for rule in changes.get('new', [])):
        return True
    return (changes.get('current') or {}).get('total', 0) > (changes.get('previous') or {}).get('total', 0)


# --- backfill --------------------------------------------------------------------------


def backfill_latest(batch: int = 50, website_id: int | None = None, log=None) -> dict:
    """Sync findings from the latest report of every page that has never been synced
    (``suppressed_counts`` NULL). Idempotent; commits per batch; never loads photos."""
    latest_ts = db.session.query(Report.site_id, func.max(Report.timestamp).label('ts'))
    if website_id is not None:
        latest_ts = latest_ts.join(Site_Website_Assoc, Site_Website_Assoc.c.site_id == Report.site_id).filter(
            Site_Website_Assoc.c.website_id == website_id
        )
    latest_ts = latest_ts.group_by(Report.site_id).subquery()
    ids = [
        row.id for row in
        db.session.query(Report.id)
        .join(latest_ts, (latest_ts.c.site_id == Report.site_id) & (latest_ts.c.ts == Report.timestamp))
        .filter(Report.suppressed_counts.is_(None))
        .order_by(Report.id)
        .all()
    ]
    stats = {'reports': 0, 'new': 0, 'skipped': 0}
    for start in range(0, len(ids), batch):
        chunk = ids[start:start + batch]
        rows = (
            db.session.query(Report.id, Report.site_id, Report.timestamp, Report.report)
            .filter(Report.id.in_(chunk))
            .all()
        )
        for row in rows:
            result = sync_report_findings(row.site_id, row.id, row.timestamp, (row.report or {}).get('violations') or [])
            refresh_suppressed_counts(row.site_id, row.id)
            stats['reports'] += 1
            stats['new'] += result.new
        db.session.commit()
        db.session.expunge_all()
        if log:
            log(f"synced {min(start + batch, len(ids))}/{len(ids)} reports")
    return stats

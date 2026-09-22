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

from sqlalchemy import func

from models import db
from models.finding import Finding, SUPPRESSED_STATUSES
from models.report import Report
from models.website import Site_Website_Assoc

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
                html=normalise_html(node.get('html')), first_seen=report_ts, last_seen=report_ts,
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

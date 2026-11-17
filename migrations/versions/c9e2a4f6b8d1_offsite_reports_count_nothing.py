"""Reports whose scan ended on another site count nothing.

A page that redirects off the website when scanned (a login page sent to CAS, say) is
not the owner's to fix. New reports like that get a suppression snapshot covering
every failing rule (services.findings.record_report_findings); this gives the existing
ones the same snapshot. Reads only url, base_url and report_counts, never the report
JSON or photos. The findings recorded from them are left as they are: they no longer
belong to a current report (services.findings.latest_report_ids), so nothing lists them.

Revision ID: c9e2a4f6b8d1
Revises: f5a8b2c4d7e9
Create Date: 2026-11-17
"""
import json

import sqlalchemy as sa
from alembic import op

revision = 'c9e2a4f6b8d1'
down_revision = 'f5a8b2c4d7e9'
branch_labels = None
depends_on = None


def upgrade():
    from services.findings import offsite_counts
    from utils.urls import is_offsite

    conn = op.get_bind()
    rows = conn.execute(sa.text('SELECT id, url, base_url, report_counts FROM report')).fetchall()
    for report_id, url, base_url, report_counts in rows:
        if not is_offsite(url, base_url):
            continue
        counts = json.loads(report_counts) if isinstance(report_counts, str) else report_counts
        conn.execute(
            sa.text('UPDATE report SET suppressed_counts = :counts WHERE id = :id'),
            {'counts': json.dumps(offsite_counts(counts)), 'id': report_id},
        )


def downgrade():
    # The previous snapshots are not kept; `flask findings backfill` recomputes any
    # report whose suppressed_counts is NULL.
    conn = op.get_bind()
    from utils.urls import is_offsite

    rows = conn.execute(sa.text('SELECT id, url, base_url FROM report')).fetchall()
    for report_id, url, base_url in rows:
        if is_offsite(url, base_url):
            conn.execute(sa.text('UPDATE report SET suppressed_counts = NULL WHERE id = :id'), {'id': report_id})

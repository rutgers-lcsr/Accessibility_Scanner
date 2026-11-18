"""Status history of findings: who changed a finding's status, when, why, and how.

Append-only (models.finding.FindingStatusChange). Existing findings get one row each for
the verdict a person already gave (status_by set), so the ledger starts complete for the
latest verdicts; earlier ones were overwritten before this table existed.

Revision ID: d3b7f1a9c5e2
Revises: c9e2a4f6b8d1
Create Date: 2026-11-18
"""
import sqlalchemy as sa
from alembic import op

revision = 'd3b7f1a9c5e2'
down_revision = 'c9e2a4f6b8d1'
branch_labels = None
depends_on = None


def upgrade():
    # app.py runs create_all on start (also under `flask db upgrade`), so the table may
    # already exist, empty: create it only if missing, backfill only if empty.
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if 'finding_status_change' not in inspector.get_table_names():
        op.create_table(
            'finding_status_change',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('finding_id', sa.Integer(), sa.ForeignKey('finding.id', ondelete='CASCADE'), nullable=False),
            sa.Column('old_status', sa.String(length=20), nullable=True),
            sa.Column('new_status', sa.String(length=20), nullable=False),
            sa.Column('note', sa.Text(), nullable=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
            sa.Column('scope', sa.String(length=20), nullable=False, server_default='element'),
            sa.Column('batch_size', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('created_at', sa.DateTime(), nullable=False),
        )
    indexes = {index['name'] for index in sa.inspect(conn).get_indexes('finding_status_change')}
    if 'ix_finding_status_change_finding_id' not in indexes:
        op.create_index('ix_finding_status_change_finding_id', 'finding_status_change', ['finding_id'])
    if conn.execute(sa.text('SELECT COUNT(*) FROM finding_status_change')).scalar() == 0:
        op.execute(
            "INSERT INTO finding_status_change (finding_id, old_status, new_status, note, user_id, scope, batch_size, created_at) "
            "SELECT id, NULL, status, note, status_by, 'element', 1, COALESCE(status_at, updated_at, created_at) "
            "FROM finding WHERE status_by IS NOT NULL"
        )


def downgrade():
    op.drop_index('ix_finding_status_change_finding_id', table_name='finding_status_change')
    op.drop_table('finding_status_change')

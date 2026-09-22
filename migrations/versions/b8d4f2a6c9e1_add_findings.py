"""add finding table and report.suppressed_counts

Findings track one failing element per page across scans; suppressed_counts is the
per-report snapshot of rules whose findings are all suppressed.

Revision ID: b8d4f2a6c9e1
Revises: b8d4f0a2c6e1
Create Date: 2026-09-22 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b8d4f2a6c9e1'
down_revision = 'b8d4f0a2c6e1'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if 'finding' not in inspector.get_table_names():
        op.create_table(
            'finding',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('site_id', sa.Integer(), nullable=False),
            sa.Column('rule_id', sa.String(length=100), nullable=False),
            sa.Column('fingerprint', sa.String(length=40), nullable=False),
            sa.Column('impact', sa.String(length=20), nullable=True),
            sa.Column('help', sa.String(length=500), nullable=True),
            sa.Column('help_url', sa.String(length=500), nullable=True),
            sa.Column('selector', sa.Text(), nullable=True),
            sa.Column('html', sa.Text(), nullable=True),
            sa.Column('first_seen', sa.DateTime(), nullable=False),
            sa.Column('last_seen', sa.DateTime(), nullable=False),
            sa.Column('last_report_id', sa.Integer(), nullable=True),
            sa.Column('status', sa.String(length=20), nullable=False),
            sa.Column('status_by', sa.Integer(), nullable=True),
            sa.Column('status_at', sa.DateTime(), nullable=True),
            sa.Column('note', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['site_id'], ['site.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['last_report_id'], ['report.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['status_by'], ['users.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('site_id', 'fingerprint', name='uq_finding_site_fingerprint'),
        )
        op.create_index('ix_finding_site_id', 'finding', ['site_id'])
        op.create_index('ix_finding_site_status', 'finding', ['site_id', 'status'])

    columns = [col['name'] for col in inspector.get_columns('report')]
    if 'suppressed_counts' not in columns:
        with op.batch_alter_table('report', schema=None) as batch_op:
            batch_op.add_column(sa.Column('suppressed_counts', sa.JSON(), nullable=True))


def downgrade():
    with op.batch_alter_table('report', schema=None) as batch_op:
        batch_op.drop_column('suppressed_counts')
    op.drop_index('ix_finding_site_status', table_name='finding')
    op.drop_index('ix_finding_site_id', table_name='finding')
    op.drop_table('finding')

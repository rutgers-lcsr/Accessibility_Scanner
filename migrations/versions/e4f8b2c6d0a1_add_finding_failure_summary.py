"""add finding.failure_summary

axe's failureSummary for the element, so the fix-first view and the emails can say
what to fix without reading the report JSON.

Revision ID: e4f8b2c6d0a1
Revises: d2e8f4a0b6c3
Create Date: 2026-09-24 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e4f8b2c6d0a1'
down_revision = 'd2e8f4a0b6c3'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {column['name'] for column in inspector.get_columns('finding')}
    if 'failure_summary' not in columns:
        op.add_column('finding', sa.Column('failure_summary', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('finding', 'failure_summary')

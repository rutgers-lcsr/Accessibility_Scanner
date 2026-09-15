"""add last_scan_status and last_scan_error to website and site

Revision ID: d9e4a7c3b5f1
Revises: c8d3f6b2a1e7
Create Date: 2026-09-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd9e4a7c3b5f1'
down_revision = 'c8d3f6b2a1e7'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    for table in ('website', 'site'):
        columns = [col['name'] for col in inspector.get_columns(table)]
        with op.batch_alter_table(table, schema=None) as batch_op:
            if 'last_scan_status' not in columns:
                batch_op.add_column(sa.Column('last_scan_status', sa.String(length=20), nullable=True))
            if 'last_scan_error' not in columns:
                batch_op.add_column(sa.Column('last_scan_error', sa.Text(), nullable=True))


def downgrade():
    for table in ('website', 'site'):
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.drop_column('last_scan_error')
            batch_op.drop_column('last_scan_status')

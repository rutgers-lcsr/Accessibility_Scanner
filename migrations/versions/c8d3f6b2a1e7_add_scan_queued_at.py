"""add scan_queued_at to website and site

Revision ID: c8d3f6b2a1e7
Revises: b7c2e5a9d1f4
Create Date: 2026-09-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c8d3f6b2a1e7'
down_revision = 'b7c2e5a9d1f4'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    for table in ('website', 'site'):
        columns = [col['name'] for col in inspector.get_columns(table)]
        if 'scan_queued_at' not in columns:
            with op.batch_alter_table(table, schema=None) as batch_op:
                batch_op.add_column(sa.Column('scan_queued_at', sa.DateTime(), nullable=True))


def downgrade():
    for table in ('website', 'site'):
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.drop_column('scan_queued_at')

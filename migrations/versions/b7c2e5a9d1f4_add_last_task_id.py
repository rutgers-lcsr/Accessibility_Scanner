"""add last_task_id to website and site

Revision ID: b7c2e5a9d1f4
Revises: d3948d1d82d7
Create Date: 2026-09-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b7c2e5a9d1f4'
down_revision = 'd3948d1d82d7'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    for table in ('website', 'site'):
        columns = [col['name'] for col in inspector.get_columns(table)]
        if 'last_task_id' not in columns:
            with op.batch_alter_table(table, schema=None) as batch_op:
                batch_op.add_column(sa.Column('last_task_id', sa.String(length=36), nullable=True))

    # Scans already running at upgrade time keep resolving to their website.
    op.execute("UPDATE website SET last_task_id = current_task_id WHERE current_task_id IS NOT NULL")


def downgrade():
    for table in ('website', 'site'):
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.drop_column('last_task_id')

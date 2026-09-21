"""add last_notified to website

When the website's admin and users were last emailed.

Revision ID: a7c3e9f1b5d2
Revises: f6a2b8d4c9e3
Create Date: 2026-09-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a7c3e9f1b5d2'
down_revision = 'f6a2b8d4c9e3'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('website')]
    if 'last_notified' not in columns:
        with op.batch_alter_table('website', schema=None) as batch_op:
            batch_op.add_column(sa.Column('last_notified', sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table('website', schema=None) as batch_op:
        batch_op.drop_column('last_notified')

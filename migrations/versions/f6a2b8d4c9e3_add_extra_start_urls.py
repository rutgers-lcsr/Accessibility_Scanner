"""add extra_start_urls to website

Pages a full scan starts from besides the website URL, for websites whose sections
are not linked from the root.

Revision ID: f6a2b8d4c9e3
Revises: e5f1c9d7a3b2
Create Date: 2026-09-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f6a2b8d4c9e3'
down_revision = 'e5f1c9d7a3b2'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('website')]
    if 'extra_start_urls' not in columns:
        with op.batch_alter_table('website', schema=None) as batch_op:
            batch_op.add_column(sa.Column('extra_start_urls', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('website', schema=None) as batch_op:
        batch_op.drop_column('extra_start_urls')

"""add notification_opt_out

Per-user opt-out from a website's notification emails, so unsubscribing no longer
switches email off for everyone on the website.

Revision ID: b8d4f0a2c6e1
Revises: a7c3e9f1b5d2
Create Date: 2026-09-22 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b8d4f0a2c6e1'
down_revision = 'a7c3e9f1b5d2'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if 'notification_opt_out' in inspector.get_table_names():
        return
    op.create_table(
        'notification_opt_out',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('website_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['website_id'], ['website.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'website_id'),
    )


def downgrade():
    op.drop_table('notification_opt_out')

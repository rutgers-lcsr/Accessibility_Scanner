"""add owner engagement and reminder state

users.last_login and users.last_digest_at, the website's reminder columns, and the
website_view table (when a website's own people last opened its page).

Revision ID: f5a9c3d7e1b2
Revises: e4f8b2c6d0a1
Create Date: 2026-09-24 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f5a9c3d7e1b2'
down_revision = 'e4f8b2c6d0a1'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    users = {column['name'] for column in inspector.get_columns('users')}
    if 'last_login' not in users:
        op.add_column('users', sa.Column('last_login', sa.DateTime(), nullable=True))
    if 'last_digest_at' not in users:
        op.add_column('users', sa.Column('last_digest_at', sa.DateTime(), nullable=True))

    website = {column['name'] for column in inspector.get_columns('website')}
    if 'attention_since' not in website:
        op.add_column('website', sa.Column('attention_since', sa.DateTime(), nullable=True))
    if 'last_reminded_at' not in website:
        op.add_column('website', sa.Column('last_reminded_at', sa.DateTime(), nullable=True))
    if 'escalated_at' not in website:
        op.add_column('website', sa.Column('escalated_at', sa.DateTime(), nullable=True))
    if 'reminder_count' not in website:
        op.add_column('website', sa.Column('reminder_count', sa.Integer(), nullable=False, server_default='0'))

    if 'website_view' not in inspector.get_table_names():
        op.create_table(
            'website_view',
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('website_id', sa.Integer(), nullable=False),
            sa.Column('last_viewed_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['website_id'], ['website.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('user_id', 'website_id'),
        )


def downgrade():
    op.drop_table('website_view')
    op.drop_column('website', 'reminder_count')
    op.drop_column('website', 'escalated_at')
    op.drop_column('website', 'last_reminded_at')
    op.drop_column('website', 'attention_since')
    op.drop_column('users', 'last_digest_at')
    op.drop_column('users', 'last_login')

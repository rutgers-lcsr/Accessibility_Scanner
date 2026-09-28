"""add link and link_source

Links (any host) found on a website's pages, with the result of the reachability
check, and the pages each one is on with its link text.

Revision ID: a9d5c1e7f3b4
Revises: f5a9c3d7e1b2
Create Date: 2026-09-28 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a9d5c1e7f3b4'
down_revision = 'f5a9c3d7e1b2'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    if 'link' not in tables:
        op.create_table(
            'link',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('website_id', sa.Integer(), nullable=False),
            sa.Column('url', sa.String(length=1000), nullable=False),
            sa.Column('external', sa.Boolean(), nullable=False),
            sa.Column('status', sa.String(length=16), nullable=False),
            sa.Column('status_code', sa.Integer(), nullable=True),
            sa.Column('final_url', sa.String(length=1000), nullable=True),
            sa.Column('error', sa.Text(), nullable=True),
            sa.Column('first_seen', sa.DateTime(), nullable=False),
            sa.Column('last_seen', sa.DateTime(), nullable=False),
            sa.Column('checked_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['website_id'], ['website.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('website_id', 'url', name='uq_link_website_url'),
        )
        op.create_index('ix_link_website_id', 'link', ['website_id'])
        op.create_index('ix_link_website_status', 'link', ['website_id', 'status'])
    if 'link_source' not in tables:
        op.create_table(
            'link_source',
            sa.Column('link_id', sa.Integer(), nullable=False),
            sa.Column('site_id', sa.Integer(), nullable=False),
            sa.Column('text', sa.String(length=300), nullable=True),
            sa.ForeignKeyConstraint(['link_id'], ['link.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['site_id'], ['site.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('link_id', 'site_id'),
        )


def downgrade():
    op.drop_table('link_source')
    op.drop_index('ix_link_website_status', table_name='link')
    op.drop_index('ix_link_website_id', table_name='link')
    op.drop_table('link')

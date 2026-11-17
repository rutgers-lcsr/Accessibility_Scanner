"""add crawl inventories: page content tracking, media, third-party hosts, vendors

Revision ID: d3e6f9a2b5c7
Revises: c2d5e8f1a4b6
Create Date: 2026-11-17 00:00:02.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd3e6f9a2b5c7'
down_revision = 'c2d5e8f1a4b6'
branch_labels = None
depends_on = None


def _site_columns():
    return [
        sa.Column('content_hash', sa.String(40), nullable=True),
        sa.Column('content_changed_at', sa.DateTime(), nullable=True),
        sa.Column('last_modified', sa.DateTime(), nullable=True),
        sa.Column('mixed_content', sa.JSON(), nullable=True),
    ]


def upgrade():
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    existing = {col['name'] for col in inspector.get_columns('site')}
    with op.batch_alter_table('site', schema=None) as batch_op:
        for column in _site_columns():
            if column.name not in existing:
                batch_op.add_column(column)

    if 'media_item' not in tables:
        op.create_table(
            'media_item',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('website_id', sa.Integer(), sa.ForeignKey('website.id', ondelete='CASCADE'), nullable=False),
            sa.Column('url', sa.String(1000), nullable=False),
            sa.Column('kind', sa.String(10), nullable=False),
            sa.Column('provider', sa.String(50), nullable=True),
            sa.Column('captions', sa.String(10), nullable=False, server_default='unknown'),
            sa.Column('audio_description', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('caption_override', sa.String(10), nullable=True),
            sa.Column('note', sa.Text(), nullable=True),
            sa.Column('override_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
            sa.Column('override_at', sa.DateTime(), nullable=True),
            sa.Column('first_seen', sa.DateTime(), nullable=False),
            sa.Column('last_seen', sa.DateTime(), nullable=False),
            sa.UniqueConstraint('website_id', 'url', name='uq_media_website_url'),
        )
        op.create_index('ix_media_item_website_id', 'media_item', ['website_id'])
    if 'media_source' not in tables:
        op.create_table(
            'media_source',
            sa.Column('media_id', sa.Integer(), sa.ForeignKey('media_item.id', ondelete='CASCADE'), primary_key=True),
            sa.Column('site_id', sa.Integer(), sa.ForeignKey('site.id', ondelete='CASCADE'), primary_key=True),
        )
    if 'third_party_host' not in tables:
        op.create_table(
            'third_party_host',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('website_id', sa.Integer(), sa.ForeignKey('website.id', ondelete='CASCADE'), nullable=False),
            sa.Column('host', sa.String(255), nullable=False),
            sa.Column('kinds', sa.String(100), nullable=False, server_default=''),
            sa.Column('example_url', sa.String(1000), nullable=True),
            sa.Column('page_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('pages', sa.JSON(), nullable=True),
            sa.Column('first_seen', sa.DateTime(), nullable=False),
            sa.Column('last_seen', sa.DateTime(), nullable=False),
            sa.UniqueConstraint('website_id', 'host', name='uq_third_party_website_host'),
        )
        op.create_index('ix_third_party_host', 'third_party_host', ['host'])
    if 'vendor' not in tables:
        op.create_table(
            'vendor',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('name', sa.String(200), nullable=False),
            sa.Column('hosts', sa.Text(), nullable=False),
            sa.Column('status', sa.String(20), nullable=False, server_default='under_review'),
            sa.Column('vpat_url', sa.String(1000), nullable=True),
            sa.Column('vpat_date', sa.Date(), nullable=True),
            sa.Column('review_due', sa.Date(), nullable=True),
            sa.Column('contact', sa.String(300), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
        )


def downgrade():
    op.drop_table('vendor')
    op.drop_index('ix_third_party_host', table_name='third_party_host')
    op.drop_table('third_party_host')
    op.drop_table('media_source')
    op.drop_index('ix_media_item_website_id', table_name='media_item')
    op.drop_table('media_item')
    with op.batch_alter_table('site', schema=None) as batch_op:
        for column in reversed(_site_columns()):
            batch_op.drop_column(column.name)

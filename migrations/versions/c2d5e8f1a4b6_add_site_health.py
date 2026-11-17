"""add site health: health_check, website_health, content_requirement, website_requirement

Revision ID: c2d5e8f1a4b6
Revises: b1c4d7e9f2a3
Create Date: 2026-11-17 00:00:01.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c2d5e8f1a4b6'
down_revision = 'b1c4d7e9f2a3'
branch_labels = None
depends_on = None


def upgrade():
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if 'health_check' not in tables:
        op.create_table(
            'health_check',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('website_id', sa.Integer(), sa.ForeignKey('website.id', ondelete='CASCADE'), nullable=False),
            sa.Column('checked_at', sa.DateTime(), nullable=False),
            sa.Column('up', sa.Boolean(), nullable=False),
            sa.Column('status_code', sa.Integer(), nullable=True),
            sa.Column('response_ms', sa.Integer(), nullable=True),
            sa.Column('error', sa.String(500), nullable=True),
        )
        op.create_index('ix_health_check_website_time', 'health_check', ['website_id', 'checked_at'])
    if 'website_health' not in tables:
        op.create_table(
            'website_health',
            sa.Column('website_id', sa.Integer(), sa.ForeignKey('website.id', ondelete='CASCADE'), primary_key=True),
            sa.Column('checked_at', sa.DateTime(), nullable=False),
            sa.Column('up', sa.Boolean(), nullable=False),
            sa.Column('status_code', sa.Integer(), nullable=True),
            sa.Column('response_ms', sa.Integer(), nullable=True),
            sa.Column('error', sa.String(500), nullable=True),
            sa.Column('final_url', sa.String(1000), nullable=True),
            sa.Column('up_changed_at', sa.DateTime(), nullable=True),
            sa.Column('https_redirect', sa.Boolean(), nullable=True),
            sa.Column('tls_valid', sa.Boolean(), nullable=True),
            sa.Column('tls_expires_at', sa.DateTime(), nullable=True),
            sa.Column('tls_issuer', sa.String(300), nullable=True),
            sa.Column('tls_error', sa.String(500), nullable=True),
            sa.Column('security_headers', sa.JSON(), nullable=True),
            sa.Column('platform', sa.String(100), nullable=True),
            sa.Column('platform_version', sa.String(100), nullable=True),
            sa.Column('server', sa.String(200), nullable=True),
            sa.Column('requirements', sa.JSON(), nullable=True),
        )
    if 'content_requirement' not in tables:
        op.create_table(
            'content_requirement',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('name', sa.String(200), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('check_type', sa.String(20), nullable=False),
            sa.Column('pattern', sa.String(500), nullable=False),
            sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
        )
    if 'website_requirement' not in tables:
        op.create_table(
            'website_requirement',
            sa.Column('website_id', sa.Integer(), sa.ForeignKey('website.id', ondelete='CASCADE'), primary_key=True),
            sa.Column('requirement_id', sa.Integer(), sa.ForeignKey('content_requirement.id', ondelete='CASCADE'), primary_key=True),
        )


def downgrade():
    op.drop_table('website_requirement')
    op.drop_table('content_requirement')
    op.drop_table('website_health')
    op.drop_index('ix_health_check_website_time', table_name='health_check')
    op.drop_table('health_check')

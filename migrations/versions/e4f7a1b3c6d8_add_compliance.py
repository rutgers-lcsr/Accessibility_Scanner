"""add compliance: compliance_exception and manual_review

Revision ID: e4f7a1b3c6d8
Revises: d3e6f9a2b5c7
Create Date: 2026-11-17 00:00:03.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e4f7a1b3c6d8'
down_revision = 'd3e6f9a2b5c7'
branch_labels = None
depends_on = None


def upgrade():
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if 'compliance_exception' not in tables:
        op.create_table(
            'compliance_exception',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('website_id', sa.Integer(), sa.ForeignKey('website.id', ondelete='CASCADE'), nullable=False),
            sa.Column('rule_id', sa.String(100), nullable=True),
            sa.Column('url_prefix', sa.String(500), nullable=True),
            sa.Column('kind', sa.String(30), nullable=False),
            sa.Column('reason', sa.Text(), nullable=False),
            sa.Column('status', sa.String(20), nullable=False, server_default='requested'),
            sa.Column('requested_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
            sa.Column('requested_at', sa.DateTime(), nullable=False),
            sa.Column('decided_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
            sa.Column('decided_at', sa.DateTime(), nullable=True),
            sa.Column('decision_note', sa.Text(), nullable=True),
            sa.Column('expires_on', sa.Date(), nullable=True),
        )
        op.create_index('ix_compliance_exception_website_id', 'compliance_exception', ['website_id'])
    if 'manual_review' not in tables:
        op.create_table(
            'manual_review',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('website_id', sa.Integer(), sa.ForeignKey('website.id', ondelete='CASCADE'), nullable=False),
            sa.Column('reviewer_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
            sa.Column('source', sa.String(10), nullable=False, server_default='person'),
            sa.Column('tool', sa.String(200), nullable=True),
            sa.Column('status', sa.String(20), nullable=False, server_default='in_progress'),
            sa.Column('pages', sa.JSON(), nullable=True),
            sa.Column('results', sa.JSON(), nullable=True),
            sa.Column('summary', sa.Text(), nullable=True),
            sa.Column('started_at', sa.DateTime(), nullable=False),
            sa.Column('completed_at', sa.DateTime(), nullable=True),
        )
        op.create_index('ix_manual_review_website_id', 'manual_review', ['website_id'])


def downgrade():
    op.drop_index('ix_manual_review_website_id', table_name='manual_review')
    op.drop_table('manual_review')
    op.drop_index('ix_compliance_exception_website_id', table_name='compliance_exception')
    op.drop_table('compliance_exception')

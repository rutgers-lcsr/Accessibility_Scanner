"""add document and document_site_assoc

Documents (PDF, Word, PowerPoint, Excel) linked from a website's pages, with the
result of the basic PDF checks.

Revision ID: d2e8f4a0b6c3
Revises: c1d7e3f9a5b2
Create Date: 2026-09-22 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd2e8f4a0b6c3'
down_revision = 'c1d7e3f9a5b2'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    if 'document' not in tables:
        op.create_table(
            'document',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('website_id', sa.Integer(), nullable=False),
            sa.Column('url', sa.String(length=1000), nullable=False),
            sa.Column('doc_type', sa.String(length=8), nullable=False),
            sa.Column('status', sa.String(length=16), nullable=False),
            sa.Column('first_seen', sa.DateTime(), nullable=False),
            sa.Column('last_seen', sa.DateTime(), nullable=False),
            sa.Column('checked_at', sa.DateTime(), nullable=True),
            sa.Column('size_bytes', sa.Integer(), nullable=True),
            sa.Column('page_count', sa.Integer(), nullable=True),
            sa.Column('title', sa.String(length=500), nullable=True),
            sa.Column('has_title', sa.Boolean(), nullable=True),
            sa.Column('language', sa.String(length=32), nullable=True),
            sa.Column('error', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['website_id'], ['website.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('website_id', 'url', name='uq_document_website_url'),
        )
        op.create_index('ix_document_website_id', 'document', ['website_id'])
        op.create_index('ix_document_website_status', 'document', ['website_id', 'status'])
    if 'document_site_assoc' not in tables:
        op.create_table(
            'document_site_assoc',
            sa.Column('document_id', sa.Integer(), nullable=False),
            sa.Column('site_id', sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(['document_id'], ['document.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['site_id'], ['site.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('document_id', 'site_id'),
        )


def downgrade():
    op.drop_table('document_site_assoc')
    op.drop_index('ix_document_website_status', table_name='document')
    op.drop_index('ix_document_website_id', table_name='document')
    op.drop_table('document')

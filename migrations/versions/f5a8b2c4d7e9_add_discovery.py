"""add site discovery: discovered_host and domain discovery columns

Revision ID: f5a8b2c4d7e9
Revises: e4f7a1b3c6d8
Create Date: 2026-11-17 00:00:04.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f5a8b2c4d7e9'
down_revision = 'e4f7a1b3c6d8'
branch_labels = None
depends_on = None


def _domain_columns():
    return [
        sa.Column('discovery_enabled', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('discovered_at', sa.DateTime(), nullable=True),
        sa.Column('discovery_error', sa.String(300), nullable=True),
    ]


def upgrade():
    inspector = sa.inspect(op.get_bind())
    existing = {col['name'] for col in inspector.get_columns('domains')}
    with op.batch_alter_table('domains', schema=None) as batch_op:
        for column in _domain_columns():
            if column.name not in existing:
                batch_op.add_column(column)
    if 'discovered_host' not in set(inspector.get_table_names()):
        op.create_table(
            'discovered_host',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('domain_id', sa.Integer(), sa.ForeignKey('domains.id', ondelete='CASCADE'), nullable=False),
            sa.Column('host', sa.String(255), nullable=False),
            sa.Column('sources', sa.String(50), nullable=False, server_default=''),
            sa.Column('status', sa.String(10), nullable=False, server_default='new'),
            sa.Column('note', sa.Text(), nullable=True),
            sa.Column('first_seen', sa.DateTime(), nullable=False),
            sa.Column('last_seen', sa.DateTime(), nullable=False),
            sa.Column('resolves', sa.Boolean(), nullable=True),
            sa.Column('http_status', sa.Integer(), nullable=True),
            sa.Column('final_url', sa.String(1000), nullable=True),
            sa.Column('title', sa.String(300), nullable=True),
            sa.Column('probe_error', sa.String(500), nullable=True),
            sa.Column('checked_at', sa.DateTime(), nullable=True),
            sa.UniqueConstraint('domain_id', 'host', name='uq_discovered_domain_host'),
        )
        op.create_index('ix_discovered_host_domain_id', 'discovered_host', ['domain_id'])


def downgrade():
    op.drop_index('ix_discovered_host_domain_id', table_name='discovered_host')
    op.drop_table('discovered_host')
    with op.batch_alter_table('domains', schema=None) as batch_op:
        for column in reversed(_domain_columns()):
            batch_op.drop_column(column.name)

"""add inventory fields to website

Lifecycle status and sunset date, department, business owner, audience and
criticality.

Revision ID: b1c4d7e9f2a3
Revises: a9d5c1e7f3b4
Create Date: 2026-11-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b1c4d7e9f2a3'
down_revision = 'a9d5c1e7f3b4'
branch_labels = None
depends_on = None


def _columns():
    return [
        sa.Column('lifecycle_status', sa.String(20), nullable=False, server_default='live'),
        sa.Column('sunset_date', sa.Date(), nullable=True),
        sa.Column('department', sa.String(200), nullable=True),
        sa.Column('business_owner', sa.String(200), nullable=True),
        sa.Column('audience', sa.String(20), nullable=True),
        sa.Column('criticality', sa.String(10), nullable=True),
    ]


def upgrade():
    existing = {col['name'] for col in sa.inspect(op.get_bind()).get_columns('website')}
    with op.batch_alter_table('website', schema=None) as batch_op:
        for column in _columns():
            if column.name not in existing:
                batch_op.add_column(column)
        if 'department' not in existing:
            batch_op.create_index('ix_website_department', ['department'])


def downgrade():
    with op.batch_alter_table('website', schema=None) as batch_op:
        batch_op.drop_index('ix_website_department')
        for column in reversed(_columns()):
            batch_op.drop_column(column.name)

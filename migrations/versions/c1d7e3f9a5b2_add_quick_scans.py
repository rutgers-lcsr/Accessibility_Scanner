"""add quick_scans

Requests for ad hoc audits of one page; results live in the Celery result backend.

Revision ID: c1d7e3f9a5b2
Revises: b8d4f2a6c9e1
Create Date: 2026-09-22 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c1d7e3f9a5b2'
down_revision = 'b8d4f2a6c9e1'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if 'quick_scans' in inspector.get_table_names():
        return
    op.create_table(
        'quick_scans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.String(length=36), nullable=False),
        sa.Column('url', sa.String(length=500), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('task_id'),
    )
    op.create_index('ix_quick_scans_task_id', 'quick_scans', ['task_id'])
    op.create_index('ix_quick_scans_user_id', 'quick_scans', ['user_id'])


def downgrade():
    op.drop_index('ix_quick_scans_user_id', table_name='quick_scans')
    op.drop_index('ix_quick_scans_task_id', table_name='quick_scans')
    op.drop_table('quick_scans')

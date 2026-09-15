"""unique, indexed site.url and website.url

Duplicate site rows (same url) are merged into the lowest id first: their reports
and website associations move to the kept row. Duplicate websites are merged the
same way (site and user associations move).

Revision ID: e5f1c9d7a3b2
Revises: d9e4a7c3b5f1
Create Date: 2026-09-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e5f1c9d7a3b2'
down_revision = 'd9e4a7c3b5f1'
branch_labels = None
depends_on = None


def _merge_duplicates(conn, table, fk_moves):
    """Keep the lowest id per url; repoint ``fk_moves`` [(table, column)] at it; delete the rest."""
    url_col = sa.column('url', sa.String)
    id_col = sa.column('id', sa.Integer)
    t = sa.table(table, id_col, url_col)
    dup_urls = conn.execute(
        sa.select(t.c.url).group_by(t.c.url).having(sa.func.count() > 1)
    ).scalars().all()
    for url in dup_urls:
        ids = conn.execute(sa.select(t.c.id).where(t.c.url == url).order_by(t.c.id)).scalars().all()
        keep, dups = ids[0], ids[1:]
        for fk_table, fk_column, other_column in fk_moves:
            fk_col = sa.column(fk_column, sa.Integer)
            ft = sa.table(fk_table, fk_col, *([sa.column(other_column, sa.Integer)] if other_column else []))
            if other_column:
                # association rows: move unless the kept row already has that partner
                present = set(conn.execute(sa.select(ft.c[other_column]).where(fk_col == keep)).scalars())
                for partner in conn.execute(sa.select(ft.c[other_column]).where(fk_col.in_(dups))).scalars().all():
                    if partner not in present:
                        conn.execute(ft.insert().values({fk_column: keep, other_column: partner}))
                        present.add(partner)
                conn.execute(ft.delete().where(fk_col.in_(dups)))
            else:
                conn.execute(ft.update().where(fk_col.in_(dups)).values({fk_column: keep}))
        conn.execute(t.delete().where(t.c.id.in_(dups)))


def upgrade():
    conn = op.get_bind()
    _merge_duplicates(conn, 'site', [
        ('report', 'site_id', None),
        ('site_website_assoc', 'site_id', 'website_id'),
    ])
    _merge_duplicates(conn, 'website', [
        ('site_website_assoc', 'website_id', 'site_id'),
        ('user_website_assoc', 'website_id', 'user_id'),
    ])

    inspector = sa.inspect(conn)
    if 'ix_site_url' not in [ix['name'] for ix in inspector.get_indexes('site')]:
        with op.batch_alter_table('site', schema=None) as batch_op:
            batch_op.create_index('ix_site_url', ['url'], unique=True)
    if 'ix_website_url' not in [ix['name'] for ix in inspector.get_indexes('website')]:
        with op.batch_alter_table('website', schema=None) as batch_op:
            batch_op.create_index('ix_website_url', ['url'], unique=True)


def downgrade():
    with op.batch_alter_table('website', schema=None) as batch_op:
        batch_op.drop_index('ix_website_url')
    with op.batch_alter_table('site', schema=None) as batch_op:
        batch_op.drop_index('ix_site_url')

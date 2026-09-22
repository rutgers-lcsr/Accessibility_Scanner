"""Flask CLI commands for maintenance work: ``flask findings backfill``."""
import click
from flask.cli import AppGroup

findings_cli = AppGroup('findings', help='Maintain the findings table.')


@findings_cli.command('backfill')
@click.option('--batch', default=50, show_default=True, help='Reports per transaction.')
@click.option('--website', 'website_id', type=int, default=None, help='Only this website id.')
def backfill(batch, website_id):
    """Create findings from the latest report of every page not synced yet."""
    from services.findings import backfill_latest

    stats = backfill_latest(batch=batch, website_id=website_id, log=click.echo)
    click.echo(f"Synced {stats['reports']} reports, {stats['new']} findings created.")

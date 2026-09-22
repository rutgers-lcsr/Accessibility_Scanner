"""Flask CLI commands for maintenance work: ``flask findings backfill``,
``flask maintenance retention`` and ``flask maintenance slim-reports``."""
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


maintenance_cli = AppGroup('maintenance', help='Storage maintenance: retention and report slimming.')


@maintenance_cli.command('retention')
@click.option('--dry-run', is_flag=True, help='Print the plan without deleting anything.')
@click.option('--batch', default=200, show_default=True, help='Rows per transaction.')
def retention(dry_run, batch):
    """Delete old reports and drop old screenshots per the retention settings."""
    from services.maintenance import apply_retention, plan_retention, retention_settings

    settings = retention_settings()
    plan = plan_retention()
    click.echo(f"Keeping {settings['keep_days']} days in full, one report per month up to {settings['max_days']} days.")
    for site in plan.per_site:
        click.echo(
            f"site {site['site_id']} {site['url'] or ''}: {site['reports']} reports, "
            f"{'would delete' if dry_run else 'delete'} {site['delete']}, "
            f"{'would drop' if dry_run else 'drop'} {site['strip_photos']} screenshots, "
            f"newest kept {site['newest_kept']:%Y-%m-%d}"
        )
    summary = plan.summary
    click.echo(
        f"TOTAL: {summary['delete']} reports {'would be' if dry_run else ''} deleted, "
        f"{summary['strip_photos']} screenshots {'would be' if dry_run else ''} dropped, across {summary['sites']} pages."
    )
    if not dry_run:
        result = apply_retention(plan, batch_size=batch)
        click.echo(f"Deleted {result['deleted']} reports and dropped {result['photos_stripped']} screenshots.")


@maintenance_cli.command('slim-reports')
@click.option('--dry-run', is_flag=True, help='Count the reports that would be rewritten.')
@click.option('--batch', default=200, show_default=True, help='Rows per transaction.')
def slim_reports(dry_run, batch):
    """Strip node lists from passes/inapplicable in reports stored before slimming."""
    from services.maintenance import slim_stored_reports

    result = slim_stored_reports(batch_size=batch, dry_run=dry_run, log=click.echo)
    click.echo(
        f"Checked {result['checked']} reports; {result['rewritten']} "
        f"{'would be' if dry_run else 'were'} rewritten."
    )

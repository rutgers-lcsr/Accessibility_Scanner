"""
Celery application instance for the Accessibility Scanner.
This module initializes Celery with Redis broker for background task processing.
"""
from celery import Celery
from celery.schedules import crontab
from celery.signals import setup_logging, worker_process_init
import os
import sys
import logging

# Keep the project directory on sys.path for the life of the process. Celery's
# `-A celery_app.celery` import adds the working directory only temporarily (see
# celery.utils.imports.cwd_in_path) and removes it afterwards, before the lazy
# autodiscover_tasks() below runs. A guarded insert would be skipped inside that
# window, and `scanner` would then be unimportable in the worker.
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND, DIGEST_DAY_OF_WEEK, DIGEST_HOUR_UTC, SCAN_CHECK_INTERVAL_SECONDS

TASK_TIME_LIMIT = 3600 * 4  # hard limit for one scan


@setup_logging.connect
def config_loggers(*args, **kwargs):
    """Configure logging for Celery workers."""
    # Get the scanner logger
    scanner_logger = logging.getLogger('scanner')
    scanner_logger.setLevel(logging.INFO)

    # Create console handler with proper formatting
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)

    # Use Celery's default formatter
    formatter = logging.Formatter(
        '[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)

    # Add handler to scanner logger
    scanner_logger.addHandler(handler)
    scanner_logger.propagate = False  # Don't propagate to root logger

# Create Celery instance with configuration from environment
celery = Celery(
    'accessibility_scanner',
    broker=os.environ.get('CELERY_BROKER_URL', CELERY_BROKER_URL),
    backend=os.environ.get('CELERY_RESULT_BACKEND', CELERY_RESULT_BACKEND),
)

# Update Celery config
celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=TASK_TIME_LIMIT,
    task_soft_time_limit=3600 * 3,  # 3 hours soft limit
    # Redis redelivers a task that outlives the visibility timeout (default 1 h) to a
    # second worker, so it must exceed the hard time limit. Late acks plus
    # reject_on_worker_lost mean a task whose worker dies (OOM, SIGKILL) is redelivered
    # rather than silently lost while the website still points at it.
    broker_transport_options={'visibility_timeout': TASK_TIME_LIMIT + 600},
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,  # Only fetch one task at a time per worker
    worker_max_tasks_per_child=5,  # Each scan holds a Chromium; recycle children often
    # Task results live a day: that is how long a quick scan's result can be viewed.
    result_expires=86400,
    beat_schedule={
        'check-and-queue-scans': {
            'task': 'scanner.tasks.check_and_queue_scans',
            'schedule': float(SCAN_CHECK_INTERVAL_SECONDS),
        },
        # Weekly digest to site admins: day and hour come from the environment (beat
        # reads them at start-up); on/off is the admin_digest_enabled Setting.
        'admin-weekly-digest': {
            'task': 'scanner.tasks.send_admin_digest',
            'schedule': crontab(day_of_week=DIGEST_DAY_OF_WEEK, hour=DIGEST_HOUR_UTC, minute=0),
        },
        # Nightly report retention; a no-op (with a logged plan) until enabled in Settings.
        'prune-reports': {
            'task': 'scanner.tasks.prune_reports',
            'schedule': crontab(hour=3, minute=30),
        },
    },
)

_flask_app = None


def get_flask_app():
    """The Flask app tasks run under, built once per process (it owns the DB engine)."""
    global _flask_app
    if _flask_app is None:
        from app import create_app  # imported here to avoid a circular import
        _flask_app = create_app()
    return _flask_app


@worker_process_init.connect
def init_worker_process(**kwargs):
    """Each prefork child builds its own app. Connections inherited from the parent are
    not safe to share across processes, so any pool it got by forking is dropped."""
    app = get_flask_app()
    with app.app_context():
        from models import db
        db.engine.dispose()


class ContextTask(celery.Task):
    """Base task class that ensures tasks run within Flask app context."""
    abstract = True

    def __call__(self, *args, **kwargs):
        with get_flask_app().app_context():
            return self.run(*args, **kwargs)


celery.Task = ContextTask

# Task modules are located by package (scanner/tasks.py). Importing them here directly
# would be circular, since they import this module for the `celery` instance.
celery.autodiscover_tasks(['scanner'])

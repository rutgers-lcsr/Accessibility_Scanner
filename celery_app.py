"""
Celery application instance for the Accessibility Scanner.
This module initializes Celery with Redis broker for background task processing.
"""
from celery import Celery, Task
from celery.signals import setup_logging
from flask import Flask
import os
import sys
import logging

# Add the project directory to Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

from config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND, DEBUG

# Detect if we're running as a Celery worker
# This is true when celery worker command is executed
IS_CELERY_WORKER = 'celery' in sys.argv[0] or 'worker' in sys.argv

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
    task_time_limit=3600 * 4,  # 4 hours hard limit
    task_soft_time_limit=3600 * 3,  # 3 hours soft limit
    worker_prefetch_multiplier=1,  # Only fetch one task at a time per worker
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks to prevent memory leaks
    beat_schedule={
        'check-and-queue-scans': {
            'task': 'scanner.tasks.check_and_queue_scans',
            'schedule': 3600.0 if DEBUG else 86400.0,  # Run every hour (3600 seconds) if DEBUG is True, else once per day
        },
    },
)

# Create a context task that runs within Flask app context
class ContextTask(celery.Task):
    """Base task class that ensures tasks run within Flask app context."""
    abstract = True
    
    def __call__(self, *args, **kwargs):
        # Ensure project directory is in Python path (critical for forked workers)
        project_dir = os.path.dirname(os.path.abspath(__file__))
        if project_dir not in sys.path:
            sys.path.insert(0, project_dir)
        
        # Import here to avoid circular imports
        from app import create_app
        flask_app = create_app()
        with flask_app.app_context():
            return self.run(*args, **kwargs)

celery.Task = ContextTask

# Only import tasks when running as a worker (not during Flask app startup)
# This prevents circular imports and unnecessary Redis connections during app init
if IS_CELERY_WORKER:
    from scanner import tasks  # noqa: F401, E402


import typing
import logging
from multiprocessing import current_process

LogType = typing.Literal['info', 'warning', 'error', 'debug']

# Get logger for scanner module
logger = logging.getLogger('scanner')

def log_message(message: str, type: LogType) -> None:
    """
    Log a message using Python's logging module.
    This ensures proper integration with Celery's logging system.
    """
    if current_process().name != 'MainProcess': 
        process_id = current_process().name
        message = f"[{process_id}] {message}"

    if type == 'info':
        logger.info(message)
    elif type == 'warning':
        logger.warning(message)
    elif type == 'error':
        logger.error(message)
    elif type == 'debug':
        logger.debug(message)
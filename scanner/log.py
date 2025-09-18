import typing
from datetime import datetime
import os
from multiprocessing import current_process
LogType = typing.Literal['info', 'warning', 'error']

def log_message(message: str, type: LogType) -> None:

    if current_process().name != 'MainProcess': 
        process_id = current_process().name
        message = f"[{process_id}] {message}"

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if type == 'info':
        print(f"[{timestamp}] INFO: {message}")
    elif type == 'warning':
        print(f"[{timestamp}] WARNING: {message}")
    elif type == 'error':
        print(f"[{timestamp}] ERROR: {message}")
import typing
from datetime import datetime
LogType = typing.Literal['info', 'warning', 'error']

def log_message(message: str, type: LogType) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if type == 'info':
        print(f"[{timestamp}] INFO: {message}")
    elif type == 'warning':
        print(f"[{timestamp}] WARNING: {message}")
    elif type == 'error':
        print(f"[{timestamp}] ERROR: {message}")
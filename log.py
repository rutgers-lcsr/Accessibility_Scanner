import typing
LogType = typing.Literal['info', 'warning', 'error']

def log_message(message: str, type: LogType) -> None:
    if type == 'info':
        print(f"INFO: {message}")
    elif type == 'warning':
        print(f"WARNING: {message}")
    elif type == 'error':
        print(f"ERROR: {message}")
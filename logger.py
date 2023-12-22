import sys
import logging
import logging.config

from datetime import date

DEFAULT_LOG_LEVEL_STDOUT = 'DEBUG'
DEFAULT_LOG_LEVEL_FILE = 'INFO'


def add_date_to_file_name(file_name: str, dt: date, fmt: str = "%Y%m%d") -> str:
    """
    Takes a file name and inserts a formatted date string in front of the file extension.

    Parameters:
        file_name (str): The file name.
        dt (datetime.date): The date to format and add to the file name.
        fmt (str): Optional. The string format to apply to the date.
    Returns:
        str: The revised file name.
    """
    split = file_name.rsplit(".", 1)
    split.insert(1, dt.strftime(fmt))
    return ".".join(split)


def configure_logging(log_level: str, log_file: str = None):
    """
    Configure the logging for the session.

    Logging will always occur to stdout with this configuration.
    If no log file is provided, stdout logging level will be set to log_level.
    If a file is provided, stdout logging will proceed at its default level,
    and a file log handler will be added at log_level.

    Parameters:
        log_level (str): The string value of a logging.Level.
        log_file (str): Optional. The file to write log output to. Defaults to None.
    """
    config = {
        'version': 1,
        'filters': {},
        'formatters': {
            'formatter': {
                'format': '%(asctime)s::%(levelname)s::%(module)s::%(funcName)s()::%(lineno)d::%(message)s'
            }
        },
        'handlers': {
            'console_stdout': {
                'class': 'logging.StreamHandler',
                'level': log_level if not log_file else DEFAULT_LOG_LEVEL_STDOUT,
                'formatter': 'formatter',
                'stream': sys.stdout
            },
        },
        'root': {
            'level': 'NOTSET',
            'handlers': ['console_stdout']
        },
    }

    if log_file:
        today = date.today()
        log_file = add_date_to_file_name(log_file, today, "%Y%m%d")

        config["handlers"]["file"] = {
            "class": "logging.FileHandler",
            "level": log_level,
            "formatter": "formatter",
            "filename": log_file,
            "encoding": "utf8"
        }
        config["root"]["handlers"].append("file")

    logging.config.dictConfig(config)

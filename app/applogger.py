"""
This module configures logging for the FastAPI-Azure-Container-App.
It sets up logging to console, file, and Papertrail using a dictionary configuration.
The logging configuration includes:
- A default formatter with a specific format and date format.
- Handlers for console output, file output, and Papertrail SysLog.
- A logger for the module with DEBUG level and handlers for file and Papertrail.
Attributes:
    PAPERTRAILHOST (str): The hostname for the Papertrail logging service.
    PAPERTRAILPORT (int): The port number for the Papertrail logging service.
    config_dict (dict): The dictionary configuration for logging.
Example:
    The logger can be used as follows:
    ```
    ```
"""

import logging
import logging.config

# from logging.handlers import SysLogHandler

PAPERTRAILHOST = "logs2.papertrailapp.com"
PAPERTRAILPORT = 41485

config_dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        },
        "papertrail": {
            "class": "logging.handlers.SysLogHandler",
            "formatter": "default",
            "address": ("logs2.papertrailapp.com", 41485),
        },
        "file": {
            "class": "logging.FileHandler",
            "formatter": "default",
            "filename": "app.log",
        },
    },
    "loggers": {
        __name__: {
            "level": "DEBUG",
            "handlers": ["file", "papertrail"],
            "propagate": False,
        },
    },
}

logging.config.dictConfig(config_dict)
logger = logging.getLogger(__name__)
logger.info("Starting FastAPI-Azure-Container-App")


# logger.setLevel(logging.INFO)
# handler = SysLogHandler(address=(PAPERTRAILHOST, PAPERTRAILPORT))
# formatter = logging.Formatter(
#     fmt="%(asctime)s %(name)s %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
# )
# handler.setFormatter(formatter)
# logger.addHandler(handler)

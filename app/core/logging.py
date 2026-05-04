"""Logging configuration for the application.

Configures a named logger (``api_logger``) writing to the console, a local file,
and Papertrail via SysLogHandler.  Import ``logger`` from this module.
"""

import logging
import logging.config

PAPERTRAILHOST = "logs2.papertrailapp.com"
PAPERTRAILPORT = 41485

config_dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s %(name)s %(levelname)s [%(module)s:%(funcName)s:%(lineno)d] %(message)s",
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
            "address": (PAPERTRAILHOST, PAPERTRAILPORT),
        },
        "file": {
            "class": "logging.FileHandler",
            "formatter": "default",
            "filename": "app.log",
        },
    },
    "loggers": {
        "api_logger": {
            "level": "DEBUG",
            "handlers": ["console", "file", "papertrail"],
            "propagate": False,
        },
    },
}

logging.config.dictConfig(config_dict)
logger = logging.getLogger("api_logger")
logger.info("Starting FastAPI logging")

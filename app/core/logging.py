"""
This module configures logging for the FastAPI-Azure-Container-App.
It sets up logging to console, a file, and Papertrail using the SysLogHandler.
The logging configuration includes a formatter that specifies the log message format and date format.
Constants:
    PAPERTRAILHOST (str): The hostname for the Papertrail logging service.
    PAPERTRAILPORT (int): The port number for the Papertrail logging service.
Configuration Dictionary:
    config_dict (dict): A dictionary containing the logging configuration.
Logger:
    logger (logging.Logger): The logger instance configured for the application.
Usage:
    Import this module to configure logging for the application.
    The logger instance can be used to log messages throughout the application.
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

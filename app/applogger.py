"""
Global Settings for Logging
"""

import logging
import logging.config
from logging.handlers import SysLogHandler

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

# logger.setLevel(logging.INFO)
# handler = SysLogHandler(address=(PAPERTRAILHOST, PAPERTRAILPORT))
# formatter = logging.Formatter(
#     fmt="%(asctime)s %(name)s %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
# )
# handler.setFormatter(formatter)
# logger.addHandler(handler)

logger.info("Starting FastAPI-Azure-Container-App")

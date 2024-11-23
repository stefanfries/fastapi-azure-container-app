"""
Global Settuings for Logging
"""

import logging
from logging.handlers import SysLogHandler

PAPERTRAILHOST = "logs2.papertrailapp.com"
PAPERTRAILPORT = 41485

logger = logging.getLogger("FastAPI")

logger.setLevel(logging.DEBUG)
handler = SysLogHandler(address=(PAPERTRAILHOST, PAPERTRAILPORT))
formatter = logging.Formatter(
    fmt="%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.info("Starting FastAPI-Azure-Container-App")

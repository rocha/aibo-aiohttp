import logging

import coloredlogs
from aiohttp import web

import aibo.app

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    fmt = "%(asctime)s %(name)s %(levelname)s %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S.%f"
    coloredlogs.install(level="DEBUG", fmt=fmt, datefmt=datefmt)
    web.run_app(aibo.app.init())

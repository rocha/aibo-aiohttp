import logging

from aiohttp import web

import aibo.app

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG, format="%(asctime)s %(levelname)s %(message)s"
    )
    web.run_app(aibo.app.init())

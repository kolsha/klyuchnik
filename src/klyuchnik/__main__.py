from __future__ import annotations

import asyncio
import logging
import sys

from klyuchnik.bot import run
from klyuchnik.config import Settings


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    settings = Settings()
    try:
        asyncio.run(run(settings))
    except (KeyboardInterrupt, SystemExit):
        logging.getLogger(__name__).info("Shutting down")
    return 0


if __name__ == "__main__":
    sys.exit(main())

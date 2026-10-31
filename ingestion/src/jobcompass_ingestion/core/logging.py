"""
logging.py

Description : logging setup of the ingestion brick.
Rules       : one call at startup, by the entry point; modules only use
              logging.getLogger(__name__).
              Logs go to standard error, one line per event.
"""

import logging


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

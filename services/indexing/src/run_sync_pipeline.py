"""Entrypoint for the catalog sync job."""

from __future__ import annotations

import os
import sys
import logging

from shared.logging_config import configure_logging
from sync_catalog_to_opensearch import main as sync_main


if __name__ == "__main__":
    try:
        sync_main()
    except Exception:
        logging.getLogger(os.environ.get("LOGGER_NAME", "movie-indexer")).exception(
            "Catalog sync pipeline failed"
        )
        sys.exit(1)

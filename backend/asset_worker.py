"""Asset import worker entrypoint.

M1 keeps this worker intentionally small: it validates asset directories and
repeatedly verifies the shared PostgreSQL connection. The actual import batch
processing will be implemented in M5.
"""

from __future__ import annotations

import logging
import os
import signal
import sys
import time
from pathlib import Path
from typing import Iterable

import psycopg2

from config import (
    ASSET_ANNOTATIONS_DIR,
    ASSET_INCOMING_DIR,
    ASSET_INGEST_ROOTS,
    ASSET_MANIFESTS_DIR,
    ASSET_ORIGINALS_DIR,
    ASSET_QUARANTINE_DIR,
    ASSET_ROOT,
    ASSET_THUMBNAILS_DIR,
    DB_CONFIG,
)
from services.asset_import_engine import process_next_queued_batch


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("asset_worker")

ASSET_WRITABLE_DIRS: tuple[str, ...] = (
    ASSET_INCOMING_DIR,
    ASSET_ORIGINALS_DIR,
    ASSET_THUMBNAILS_DIR,
    ASSET_ANNOTATIONS_DIR,
    ASSET_MANIFESTS_DIR,
    ASSET_QUARANTINE_DIR,
)

_stop_requested = False


def _handle_stop_signal(signum: int, frame: object) -> None:
    del signum, frame
    global _stop_requested
    _stop_requested = True
    logger.info("stop signal received, finishing current loop")


def ensure_asset_directories(directories: Iterable[str]) -> None:
    """Create the asset directory tree without touching existing data."""
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        logger.info("asset directory ready: %s", directory)


def validate_ingest_roots(ingest_roots: Iterable[str]) -> None:
    for root in ingest_roots:
        path = Path(root)
        if not path.is_absolute():
            logger.warning("ignoring non-absolute ingest root: %s", root)
            continue
        if not path.exists():
            logger.warning("ingest root does not exist yet: %s", root)
            continue
        logger.info("ingest root ready: %s", root)


def check_database_connection() -> None:
    connection = psycopg2.connect(**DB_CONFIG)
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    finally:
        connection.close()


def run_forever(poll_interval: float) -> None:
    ensure_asset_directories(ASSET_WRITABLE_DIRS)
    validate_ingest_roots(ASSET_INGEST_ROOTS)
    logger.info(
        "asset worker started; asset_root=%s poll_interval=%ss",
        ASSET_ROOT,
        poll_interval,
    )

    while not _stop_requested:
        try:
            check_database_connection()
            process_next_queued_batch()
        except Exception as exc:  # noqa: BLE001 - keep worker alive while db starts
            logger.warning("asset worker iteration failed: %s", exc)

        # Interruptible sleep so Docker stop stays responsive.
        for _ in range(int(max(poll_interval, 1.0))):
            if _stop_requested:
                break
            time.sleep(1.0)

    logger.info("asset worker stopped")


def main() -> int:
    signal.signal(signal.SIGTERM, _handle_stop_signal)
    signal.signal(signal.SIGINT, _handle_stop_signal)

    try:
        poll_interval = float(os.getenv("ASSET_WORKER_POLL_INTERVAL", "5"))
    except ValueError:
        logger.warning("invalid ASSET_WORKER_POLL_INTERVAL, using 5 seconds")
        poll_interval = 5.0

    run_forever(poll_interval)
    return 0


if __name__ == "__main__":
    sys.exit(main())

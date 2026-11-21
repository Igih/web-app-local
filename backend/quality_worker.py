from __future__ import annotations

import logging
import os
import signal
import time

import psycopg2
from psycopg2.extras import RealDictCursor

from config import (
    ASSET_QUALITY_DIR,
    ASSET_QUALITY_EXPORTS_DIR,
    ASSET_QUALITY_PREVIEWS_DIR,
    DB_CONFIG,
)
from services.asset_quality.csv_export_service import generate_export
from services.asset_quality.profiles import ensure_default_profiles
from services.asset_quality.quality_service import process_quality_job


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("quality_worker")

_stop_requested = False


def _handle_stop_signal(signum: int, frame: object) -> None:
    del signum, frame
    global _stop_requested
    _stop_requested = True
    logger.info("stop signal received, finishing current loop")


def _connect():
    return psycopg2.connect(**DB_CONFIG)


def _next_pending_job(conn) -> int | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id
            FROM asset.quality_jobs
            WHERE state = 'pending'
            ORDER BY id
            LIMIT 1
            FOR UPDATE SKIP LOCKED
            """
        )
        row = cur.fetchone()
    return int(row["id"]) if row else None


def _next_pending_export(conn) -> int | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id
            FROM asset.quality_exports
            WHERE state = 'pending'
            ORDER BY id
            LIMIT 1
            FOR UPDATE SKIP LOCKED
            """
        )
        row = cur.fetchone()
    return int(row["id"]) if row else None


def run_forever(poll_interval: float) -> None:
    ASSET_QUALITY_DIR.mkdir(parents=True, exist_ok=True)
    ASSET_QUALITY_PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    ASSET_QUALITY_EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

    while not _stop_requested:
        try:
            conn = _connect()
            ensure_default_profiles(conn)
            conn.commit()

            job_id = _next_pending_job(conn)
            if job_id is not None:
                logger.info("processing quality job %s", job_id)
                process_quality_job(conn, job_id)

            export_id = _next_pending_export(conn)
            if export_id is not None:
                logger.info("generating quality export %s", export_id)
                generate_export(conn, export_id)

            conn.close()
        except Exception:
            logger.exception("quality worker iteration failed")
            try:
                conn.close()
            except Exception:
                pass

        for _ in range(int(max(poll_interval, 1.0))):
            if _stop_requested:
                break
            time.sleep(1.0)

    logger.info("quality worker stopped")


def main() -> int:
    signal.signal(signal.SIGTERM, _handle_stop_signal)
    signal.signal(signal.SIGINT, _handle_stop_signal)
    try:
        poll_interval = float(os.getenv("QUALITY_WORKER_POLL_INTERVAL", "5"))
    except ValueError:
        poll_interval = 5.0
    run_forever(poll_interval)
    return 0


if __name__ == "__main__":
    main()

from __future__ import annotations

import json
import logging
import socket
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from psycopg2.extras import RealDictCursor

from config import QUALITY_ALGORITHM_VERSION, QUALITY_PREPROCESS_VERSION
from services.asset_paths import iter_image_paths
from services.asset_quality.duplicates import detect_duplicates_for_batch
from services.asset_quality.image_decoder import (
    decode_for_analysis,
    profile_key_for_candidate,
)
from services.asset_quality.metrics import calculate_metrics
from services.asset_quality.profiles import ensure_default_profiles
from services.asset_storage import sha256_file


logger = logging.getLogger("asset_quality.service")
_SOURCE_MACHINE = socket.gethostname()


def _normalized_relative_path(root: Path, path: Path) -> str:
    if root.is_file():
        return path.name
    return path.resolve().relative_to(root.resolve()).as_posix()


def _json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _batch(conn, batch_id: int) -> dict:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, batch_name, image_path, annotation_path, category_name,
                   capture_type, spectral_type, tags, recursive, status
            FROM asset.import_batches
            WHERE id = %s
            """,
            (batch_id,),
        )
        batch = cur.fetchone()
    if not batch:
        raise HTTPException(status_code=404, detail="Import batch not found")
    return batch


def create_quality_job(conn, batch_id: int, created_by: int | None = None) -> dict:
    batch = _batch(conn, batch_id)
    if batch["status"] in {"queued", "importing"}:
        raise HTTPException(status_code=409, detail="Batch is already in the import queue")

    ensure_default_profiles(conn)
    root = Path(batch["image_path"])
    image_paths = list(iter_image_paths(root, batch["recursive"]))
    if not image_paths:
        raise HTTPException(status_code=400, detail="No image files found in the source path")

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        for path in image_paths:
            normalized = _normalized_relative_path(root, path)
            stat = path.stat()
            sha256 = sha256_file(path)
            cur.execute(
                """
                INSERT INTO asset.quality_candidates (
                    batch_id, normalized_relative_path, source_path,
                    source_filename, source_machine, source_exists,
                    file_size, mtime_ns, sha256, status
                )
                VALUES (%s, %s, %s, %s, %s, TRUE, %s, %s, %s, 'pending')
                ON CONFLICT (batch_id, normalized_relative_path) DO UPDATE
                SET source_path = EXCLUDED.source_path,
                    source_filename = EXCLUDED.source_filename,
                    source_machine = EXCLUDED.source_machine,
                    source_exists = TRUE,
                    file_size = EXCLUDED.file_size,
                    mtime_ns = EXCLUDED.mtime_ns,
                    sha256 = EXCLUDED.sha256,
                    phash_64 = NULL,
                    existing_image_id = NULL,
                    duplicate_scope = NULL,
                    exact_duplicate = FALSE,
                    phash_min_distance = NULL,
                    phash_nearest_image_id = NULL,
                    phash_nearest_candidate_id = NULL,
                    similarity_coverage = 'none',
                    status = 'pending',
                    error_detail = NULL,
                    updated_at = NOW()
                """,
                (
                    batch_id,
                    normalized,
                    str(path),
                    path.name,
                    _SOURCE_MACHINE,
                    stat.st_size,
                    stat.st_mtime_ns,
                    sha256,
                ),
            )

        cur.execute(
            """
            INSERT INTO asset.quality_jobs (batch_id, state, total_count)
            VALUES (%s, 'pending', %s)
            RETURNING id
            """,
            (batch_id, len(image_paths)),
        )
        job = cur.fetchone()

    return {"job_id": job["id"], "candidate_count": len(image_paths)}


def _decode_candidate(conn, candidate: dict) -> None:
    source_path = Path(candidate["source_path"])
    if not source_path.exists():
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE asset.quality_candidates
                SET source_exists = FALSE, status = 'failed',
                    error_detail = 'source file no longer exists',
                    decode_status = 'failed',
                    updated_at = NOW()
                WHERE id = %s
                """,
                (candidate["id"],),
            )
        return

    decoded = decode_for_analysis(source_path)
    metrics = calculate_metrics(decoded, decoded["array"].dtype)
    source_fingerprint = (
        f"{candidate['sha256']}:{candidate['file_size']}:{candidate['mtime_ns']}"
    )
    profile_key = profile_key_for_candidate(
        candidate.get("capture_type"),
        candidate.get("spectral_type"),
        decoded["bit_depth"],
    )

    details = {
        "source_path": str(source_path),
        "analysis_scale": decoded["analysis_scale"],
        "alpha_policy": "ignore_alpha_keep_rgb",
        "rgb_to_gray": [0.299, 0.587, 0.114],
    }
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO asset.quality_metric_results (
                candidate_id, source_fingerprint, preprocess_version,
                algorithm_version, comparable, metric_status,
                lap_var, tenengrad, blur_effect, rms_contrast, p99_p1,
                mean_brightness, dark_fraction, bright_fraction,
                noise_sigma, noise_confidence, entropy_8bit,
                raw_min, raw_max, p01, p99,
                analysis_width, analysis_height, analysis_scale, details
            )
            VALUES (
                %s, %s, %s, %s, %s, 'ok',
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s::jsonb
            )
            ON CONFLICT (candidate_id, source_fingerprint,
                         preprocess_version, algorithm_version)
            DO UPDATE SET comparable = EXCLUDED.comparable,
                          metric_status = EXCLUDED.metric_status,
                          lap_var = EXCLUDED.lap_var,
                          tenengrad = EXCLUDED.tenengrad,
                          blur_effect = EXCLUDED.blur_effect,
                          rms_contrast = EXCLUDED.rms_contrast,
                          p99_p1 = EXCLUDED.p99_p1,
                          mean_brightness = EXCLUDED.mean_brightness,
                          dark_fraction = EXCLUDED.dark_fraction,
                          bright_fraction = EXCLUDED.bright_fraction,
                          noise_sigma = EXCLUDED.noise_sigma,
                          noise_confidence = EXCLUDED.noise_confidence,
                          entropy_8bit = EXCLUDED.entropy_8bit,
                          raw_min = EXCLUDED.raw_min,
                          raw_max = EXCLUDED.raw_max,
                          p01 = EXCLUDED.p01,
                          p99 = EXCLUDED.p99,
                          analysis_width = EXCLUDED.analysis_width,
                          analysis_height = EXCLUDED.analysis_height,
                          analysis_scale = EXCLUDED.analysis_scale,
                          details = EXCLUDED.details
            """,
            (
                candidate["id"],
                source_fingerprint,
                QUALITY_PREPROCESS_VERSION,
                QUALITY_ALGORITHM_VERSION,
                metrics["comparable"],
                metrics.get("lap_var"),
                metrics.get("tenengrad"),
                metrics["blur_effect"],
                metrics["rms_contrast"],
                metrics.get("p99_p1"),
                metrics.get("mean_brightness"),
                metrics.get("dark_fraction"),
                metrics["bright_fraction"],
                metrics["noise_sigma"],
                metrics["noise_confidence"],
                metrics.get("entropy_8bit"),
                metrics["raw_min"],
                metrics["raw_max"],
                metrics["p01"],
                metrics["p99"],
                decoded["analysis_width"],
                decoded["analysis_height"],
                decoded["analysis_scale"],
                _json_dump(details),
            ),
        )
        cur.execute(
            """
            UPDATE asset.quality_candidates
            SET decode_status = 'ok',
                width = %s,
                height = %s,
                bit_depth = %s,
                channels = %s,
                color_mode = %s,
                profile_key = %s,
                source_fingerprint = %s,
                status = 'completed',
                error_detail = NULL,
                updated_at = NOW()
            WHERE id = %s
            """,
            (
                decoded["original_width"],
                decoded["original_height"],
                decoded["bit_depth"],
                decoded["channels"],
                decoded["color_mode"],
                profile_key,
                source_fingerprint,
                candidate["id"],
            ),
        )


def process_quality_job(conn, job_id: int) -> bool:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, batch_id, state
            FROM asset.quality_jobs
            WHERE id = %s AND state = 'pending'
            FOR UPDATE SKIP LOCKED
            """,
            (job_id,),
        )
        job = cur.fetchone()
        if not job:
            return False

        cur.execute(
            """
            UPDATE asset.quality_jobs
            SET state = 'processing', started_at = NOW(), updated_at = NOW()
            WHERE id = %s
            """,
            (job_id,),
        )
        conn.commit()

    try:
        while True:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT c.id, c.batch_id, c.source_path, c.sha256,
                           c.file_size, c.mtime_ns,
                           b.capture_type, b.spectral_type
                    FROM asset.quality_candidates c
                    JOIN asset.import_batches b ON b.id = c.batch_id
                    WHERE c.batch_id = %s
                      AND c.status = 'pending'
                    ORDER BY c.id
                    LIMIT 1
                    FOR UPDATE SKIP LOCKED
                    """,
                    (job["batch_id"],),
                )
                candidate = cur.fetchone()
                if not candidate:
                    break
                cur.execute(
                    "UPDATE asset.quality_candidates SET status = 'processing', updated_at = NOW() WHERE id = %s",
                    (candidate["id"],),
                )
                conn.commit()

            try:
                _decode_candidate(conn, candidate)
            except Exception as exc:
                logger.exception("Failed to analyse quality candidate %s", candidate["id"])
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE asset.quality_candidates
                        SET decode_status = 'failed',
                            status = 'failed',
                            error_detail = %s,
                            updated_at = NOW()
                        WHERE id = %s
                        """,
                        (str(exc)[:2000], candidate["id"]),
                    )
            conn.commit()

        detect_duplicates_for_batch(conn, job["batch_id"])
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE status = 'completed') AS completed,
                    COUNT(*) FILTER (WHERE status = 'failed') AS failed
                FROM asset.quality_candidates
                WHERE batch_id = %s
                """,
                (job["batch_id"],),
            )
            stats = cur.fetchone()
            cur.execute(
                """
                UPDATE asset.quality_jobs
                SET state = 'completed',
                    processed_count = %s,
                    error_count = %s,
                    finished_at = NOW(),
                    updated_at = NOW()
                WHERE id = %s
                """,
                (stats["completed"], stats["failed"], job_id),
            )
        conn.commit()
        return True
    except Exception as exc:
        conn.rollback()
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE asset.quality_jobs
                SET state = 'failed', error = %s, updated_at = NOW()
                WHERE id = %s
                """,
                (str(exc)[:2000], job_id),
            )
        conn.commit()
        return False

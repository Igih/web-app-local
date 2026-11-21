from __future__ import annotations

import csv
import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from psycopg2.extras import RealDictCursor

from config import ASSET_QUALITY_EXPORTS_DIR
from services.asset_storage import sha256_file


logger = logging.getLogger("asset_quality.csv_export")


CSV_FIELDS = [
    "batch_id",
    "candidate_id",
    "source_relative_path",
    "original_filename",
    "category",
    "capture_type",
    "spectral_type",
    "width",
    "height",
    "bit_depth",
    "channels",
    "file_size",
    "sha256",
    "decode_status",
    "decode_error",
    "content_changed",
    "blur_effect",
    "rms_contrast",
    "noise_sigma",
    "bright_fraction",
    "exact_duplicate",
    "duplicate_scope",
    "existing_image_id",
    "phash_64",
    "phash_nearest_distance",
    "nearest_image_id",
    "nearest_candidate_id",
    "quality_flags",
    "recommendation",
    "manual_decision",
    "manual_reason",
    "metric_version",
    "preprocess_version",
    "profile_key",
    "profile_version",
    "evaluation_id",
    "exported_at",
]


def _safe_cell(value) -> str:
    if value is None:
        return ""
    text = str(value)
    if text.startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


def _row_to_dict(row: dict, evaluation_id: int, exported_at: str) -> dict:
    return {
        "batch_id": row["batch_id"],
        "candidate_id": row["candidate_id"],
        "source_relative_path": row["normalized_relative_path"],
        "original_filename": row["source_filename"],
        "category": row["category_name"],
        "capture_type": row["capture_type"],
        "spectral_type": row["spectral_type"],
        "width": row["width"],
        "height": row["height"],
        "bit_depth": row["bit_depth"],
        "channels": row["channels"],
        "file_size": row.get("file_size"),
        "sha256": row["sha256"],
        "decode_status": row["decode_status"],
        "decode_error": row.get("error_detail"),
        "content_changed": "",
        "blur_effect": row.get("blur_effect"),
        "rms_contrast": row.get("rms_contrast"),
        "noise_sigma": row.get("noise_sigma"),
        "bright_fraction": row.get("bright_fraction"),
        "exact_duplicate": row["exact_duplicate"],
        "duplicate_scope": row["duplicate_scope"],
        "existing_image_id": row["existing_image_id"],
        "phash_64": row["phash_64"],
        "phash_nearest_distance": row["phash_min_distance"],
        "nearest_image_id": row["phash_nearest_image_id"],
        "nearest_candidate_id": row["phash_nearest_candidate_id"],
        "quality_flags": ";".join(row["flags"]),
        "recommendation": row["recommendation"],
        "manual_decision": row.get("manual_decision"),
        "manual_reason": row.get("manual_reason"),
        "metric_version": row.get("algorithm_version"),
        "preprocess_version": row.get("preprocess_version"),
        "profile_key": row["profile_key"],
        "profile_version": row.get("profile_version"),
        "evaluation_id": evaluation_id,
        "exported_at": exported_at,
    }


def generate_export(conn, export_id: int) -> bool:
    ASSET_QUALITY_EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, evaluation_id, state
            FROM asset.quality_exports
            WHERE id = %s AND state = 'pending'
            FOR UPDATE SKIP LOCKED
            """,
            (export_id,),
        )
        export = cur.fetchone()
        if not export:
            return False
        cur.execute(
            "UPDATE asset.quality_exports SET state = 'processing', updated_at = NOW() WHERE id = %s",
            (export_id,),
        )
        conn.commit()

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    c.batch_id, c.id AS candidate_id,
                    c.normalized_relative_path, c.source_filename,
                    c.file_size, c.sha256, c.decode_status, c.error_detail,
                    c.width, c.height, c.bit_depth, c.channels,
                    c.exact_duplicate, c.duplicate_scope, c.existing_image_id,
                    c.phash_64, c.phash_min_distance,
                    c.phash_nearest_image_id, c.phash_nearest_candidate_id,
                    c.profile_key,
                    b.category_name, b.capture_type, b.spectral_type,
                    m.algorithm_version, m.preprocess_version,
                    m.blur_effect, m.rms_contrast, m.noise_sigma,
                    m.bright_fraction,
                    ei.recommendation, ei.flags,
                    mr.decision AS manual_decision, mr.note AS manual_reason
                FROM asset.quality_evaluation_items ei
                JOIN asset.quality_evaluations ev ON ev.id = ei.evaluation_id
                JOIN asset.quality_candidates c ON c.id = ei.candidate_id
                JOIN asset.import_batches b ON b.id = c.batch_id
                LEFT JOIN LATERAL (
                    SELECT *
                    FROM asset.quality_metric_results m
                    WHERE m.candidate_id = c.id
                    ORDER BY m.id DESC
                    LIMIT 1
                ) m ON TRUE
                LEFT JOIN LATERAL (
                    SELECT decision, note
                    FROM asset.quality_manual_reviews
                    WHERE candidate_id = c.id
                    ORDER BY reviewed_at DESC
                    LIMIT 1
                ) mr ON TRUE
                WHERE ei.evaluation_id = %s
                ORDER BY c.id
                """,
                (export["evaluation_id"],),
            )
            rows = cur.fetchall()

            cur.execute(
                """
                SELECT batch_id, profile_snapshots
                FROM asset.quality_evaluations
                WHERE id = %s
                """,
                (export["evaluation_id"],),
            )
            evaluation = cur.fetchone()

        exported_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        csv_rows = [
            _row_to_dict(
                {**row, "flags": row["flags"] or [], "profile_version": None},
                export["evaluation_id"],
                exported_at,
            )
            for row in rows
        ]
        csv_filename = f"quality-export-{export_id}.csv"
        rules_filename = f"quality-export-{export_id}.rules.json"
        csv_path = ASSET_QUALITY_EXPORTS_DIR / csv_filename
        rules_path = ASSET_QUALITY_EXPORTS_DIR / rules_filename

        fd, temp_name = tempfile.mkstemp(
            prefix=f".{csv_filename}.", suffix=".part", dir=ASSET_QUALITY_EXPORTS_DIR
        )
        os.close(fd)
        temp_path = Path(temp_name)
        with temp_path.open("w", encoding="utf-8-sig", newline="") as file_obj:
            writer = csv.DictWriter(file_obj, fieldnames=CSV_FIELDS)
            writer.writeheader()
            for item in csv_rows:
                writer.writerow({field: _safe_cell(item.get(field)) for field in CSV_FIELDS})
        os.replace(temp_path, csv_path)

        rules_temp = csv_path.with_name(f".{rules_filename}.part")
        rules_temp.write_text(
            json.dumps(
                evaluation["profile_snapshots"] if evaluation else {},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        os.replace(rules_temp, rules_path)

        file_sha256 = sha256_file(csv_path)
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE asset.quality_exports
                SET state = 'completed',
                    storage_key = %s,
                    rules_storage_key = %s,
                    csv_filename = %s,
                    rules_filename = %s,
                    row_count = %s,
                    file_sha256 = %s,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (
                    f"quality_exports/{csv_filename}",
                    f"quality_exports/{rules_filename}",
                    csv_filename,
                    rules_filename,
                    len(csv_rows),
                    file_sha256,
                    export_id,
                ),
            )
        conn.commit()
        return True
    except Exception as exc:
        conn.rollback()
        logger.exception("Failed to generate quality export %s", export_id)
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE asset.quality_exports
                SET state = 'failed', error = %s, updated_at = NOW()
                WHERE id = %s
                """,
                (str(exc)[:2000], export_id),
            )
        conn.commit()
        return False

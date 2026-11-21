from __future__ import annotations

import hashlib
import json
import logging
import math
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from psycopg2.extras import RealDictCursor

from config import ASSET_QUALITY_EXPORTS_DIR
from services.asset_quality.profiles import (
    METRIC_DEFINITIONS,
    build_default_profile_config,
    get_profile_config,
)
from services.asset_quality.quality_rule_engine import recommend_candidate
from services.asset_storage import sha256_file


logger = logging.getLogger("asset_quality.evaluation")


def _json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _merge_profile_config(profile_config: dict, draft_rules: dict | None) -> dict:
    config = json.loads(json.dumps(profile_config, ensure_ascii=False))
    config["metrics"] = {
        metric_id: rule
        for metric_id, rule in config.get("metrics", {}).items()
        if metric_id in METRIC_DEFINITIONS
    }
    if not draft_rules:
        return config
    config.setdefault("metrics", {})
    for metric_id, override in draft_rules.items():
        if metric_id not in METRIC_DEFINITIONS:
            raise HTTPException(status_code=422, detail=f"Unknown quality metric: {metric_id}")
        direction = METRIC_DEFINITIONS[metric_id]["direction"]
        if override.get("direction", direction) != direction:
            raise HTTPException(status_code=422, detail=f"Invalid direction for {metric_id}")
        config["metrics"][metric_id] = {
            **(config["metrics"].get(metric_id, {})),
            **override,
        }
        rule = config["metrics"][metric_id]
        try:
            review, severe = float(rule["review"]), float(rule["severe"])
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=f"Invalid thresholds for {metric_id}") from exc
        if not math.isfinite(review) or not math.isfinite(severe):
            raise HTTPException(status_code=422, detail=f"Threshold must be finite for {metric_id}")
        if ((direction == "high" and review > severe)
                or (direction == "low" and severe > review)):
            raise HTTPException(status_code=422, detail=f"Threshold order is invalid for {metric_id}")
        if metric_id != "noise_sigma" and not (0 <= review <= 1 and 0 <= severe <= 1):
            raise HTTPException(status_code=422, detail=f"Threshold out of range for {metric_id}")
        if metric_id == "noise_sigma" and (review < 0 or severe < 0):
            raise HTTPException(status_code=422, detail="Noise thresholds must be nonnegative")
    return config


def _profile_for_candidate(conn, candidate: dict) -> tuple[dict, int | None]:
    profile_key = candidate.get("profile_key") or "unspecified"
    row = get_profile_config(conn, profile_key)
    if not row:
        return build_default_profile_config(), None
    return row["config"], row["version"]


def _load_candidate_rows(
    conn,
    batch_id: int,
    profile_key: str | None = None,
    *,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict]:
    where_parts = ["c.batch_id = %s", "c.status IN ('completed', 'failed')"]
    params: list[Any] = [batch_id]
    if profile_key:
        where_parts.append("c.profile_key = %s")
        params.append(profile_key)

    sql = f"""
        SELECT c.id AS candidate_id, c.batch_id, c.normalized_relative_path,
               c.source_path, c.source_filename, c.file_size, c.sha256,
               c.decode_status, c.width, c.height, c.bit_depth, c.channels,
               c.color_mode, c.profile_key, c.exact_duplicate,
               c.duplicate_scope, c.existing_image_id, c.phash_64,
               c.phash_min_distance, c.phash_nearest_image_id,
               c.phash_nearest_candidate_id, c.similarity_coverage,
               c.source_fingerprint, c.status,
               b.category_name, b.capture_type, b.spectral_type,
               m.*
        FROM asset.quality_candidates c
        JOIN asset.import_batches b ON b.id = c.batch_id
        LEFT JOIN LATERAL (
            SELECT *
            FROM asset.quality_metric_results m
            WHERE m.candidate_id = c.id
            ORDER BY m.id DESC
            LIMIT 1
        ) m ON TRUE
        WHERE {' AND '.join(where_parts)}
        ORDER BY c.id
    """
    if limit is not None:
        sql += " LIMIT %s OFFSET %s"
        params.extend([limit, offset])

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def _metric_payload(row: dict) -> dict:
    return {field: row.get(field) for field in METRIC_DEFINITIONS}


def _evaluate_row(conn, row: dict, profile_config: dict) -> tuple[str, list[str]]:
    source_changed = False
    if row.get("source_fingerprint") and row.get("sha256"):
        pass
    return recommend_candidate(
        decode_status=row.get("decode_status") or "failed",
        metrics=_metric_payload(row),
        profile_config=profile_config,
        exact_duplicate=bool(row.get("exact_duplicate")),
        source_changed=source_changed,
    )


def _candidate_item(row: dict, recommendation: str, flags: list[str]) -> dict:
    return {
        "candidate_id": row["candidate_id"],
        "batch_id": row["batch_id"],
        "source_relative_path": row["normalized_relative_path"],
        "source_filename": row["source_filename"],
        "category": row["category_name"],
        "capture_type": row["capture_type"],
        "spectral_type": row["spectral_type"],
        "width": row["width"],
        "height": row["height"],
        "bit_depth": row["bit_depth"],
        "channels": row["channels"],
        "color_mode": row["color_mode"],
        "file_size": row.get("file_size"),
        "sha256": row["sha256"],
        "decode_status": row["decode_status"],
        "profile_key": row["profile_key"],
        "metrics": _metric_payload(row),
        "exact_duplicate": row["exact_duplicate"],
        "duplicate_scope": row["duplicate_scope"],
        "existing_image_id": row["existing_image_id"],
        "phash_64": row["phash_64"],
        "phash_min_distance": row["phash_min_distance"],
        "phash_nearest_image_id": row["phash_nearest_image_id"],
        "phash_nearest_candidate_id": row["phash_nearest_candidate_id"],
        "similarity_coverage": row["similarity_coverage"],
        "recommendation": recommendation,
        "flags": flags,
    }


def list_candidates(
    conn,
    batch_id: int,
    page: int,
    page_size: int,
    profile_key: str | None = None,
) -> dict:
    offset = (page - 1) * page_size
    rows = _load_candidate_rows(
        conn, batch_id, profile_key, limit=page_size, offset=offset
    )
    items = []
    for row in rows:
        config, _ = _profile_for_candidate(conn, row)
        recommendation, flags = _evaluate_row(conn, row, config)
        items.append(_candidate_item(row, recommendation, flags))

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        where = "c.batch_id = %s AND c.status IN ('completed', 'failed')"
        params: list[Any] = [batch_id]
        if profile_key:
            where += " AND c.profile_key = %s"
            params.append(profile_key)
        cur.execute(
            f"SELECT COUNT(*) AS total FROM asset.quality_candidates c WHERE {where}",
            params,
        )
        total = cur.fetchone()["total"]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def evaluate_preview(conn, batch_id: int, payload: dict) -> dict:
    profile_key = payload.get("profile_key")
    draft_rules = payload.get("draft_rules")
    rows = _load_candidate_rows(conn, batch_id, profile_key)
    counts = {"admit": 0, "review": 0, "exclude": 0}
    flag_counts: dict[str, int] = {}
    candidate_ids = set(payload.get("candidate_ids") or [])
    candidate_results = []
    recommendation_filter = payload.get("recommendation_filter")
    matching_candidates = []

    for row in rows:
        base_config, _ = _profile_for_candidate(conn, row)
        config = _merge_profile_config(base_config, draft_rules)
        recommendation, flags = _evaluate_row(conn, row, config)
        if row["candidate_id"] in candidate_ids:
            candidate_results.append({
                "candidate_id": row["candidate_id"],
                "recommendation": recommendation,
                "flags": flags,
            })
        if recommendation == recommendation_filter:
            matching_candidates.append((row, recommendation, flags))
        counts[recommendation] += 1
        for flag in flags:
            flag_counts[flag] = flag_counts.get(flag, 0) + 1

    page_size = payload.get("page_size", 20)
    requested_page = payload.get("page", 1)
    last_page = max(1, (len(matching_candidates) + page_size - 1) // page_size)
    page = min(requested_page, last_page)
    offset = (page - 1) * page_size

    return {
        "request_id": payload.get("request_id"),
        "evaluated_count": sum(counts.values()),
        "pending_count": 0,
        "counts": counts,
        "flag_counts": flag_counts,
        "candidate_results": candidate_results,
        "candidate_total": len(matching_candidates),
        "candidate_items": [
            _candidate_item(row, recommendation, flags)
            for row, recommendation, flags in matching_candidates[offset:offset + page_size]
        ],
        "page": page,
        "page_size": page_size,
        "profile_calibrated": False,
        "stale": False,
    }


def create_evaluation(
    conn,
    batch_id: int,
    payload: dict,
    created_by: int | None,
) -> dict:
    profile_key = payload.get("profile_key")
    draft_rules = payload.get("draft_rules")
    rows = _load_candidate_rows(conn, batch_id, profile_key)
    if not rows:
        raise HTTPException(status_code=400, detail="No completed candidates to evaluate")

    profile_snapshots = {}
    items: list[dict] = []
    for row in rows:
        config, version = _profile_for_candidate(conn, row)
        config = _merge_profile_config(config, draft_rules)
        recommendation, flags = _evaluate_row(conn, row, config)
        key = row["profile_key"] or "unspecified"
        profile_snapshots[key] = {"version": version, "config": config}
        items.append(
            {
                "candidate_id": row["candidate_id"],
                "recommendation": recommendation,
                "flags": flags,
            }
        )

    candidate_ids = sorted(row["candidate_id"] for row in rows)
    candidate_set_hash = hashlib.sha256(
        ",".join(map(str, candidate_ids)).encode("utf-8")
    ).hexdigest()

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            INSERT INTO asset.quality_evaluations (
                batch_id, candidate_set_hash, filters,
                profile_snapshots, status, created_by
            )
            VALUES (%s, %s, %s::jsonb, %s::jsonb, 'confirmed', %s)
            RETURNING id
            """,
            (
                batch_id,
                candidate_set_hash,
                _json_dump({"profile_key": profile_key}),
                _json_dump(profile_snapshots),
                created_by,
            ),
        )
        evaluation = cur.fetchone()
        evaluation_id = evaluation["id"]
        for item in items:
            cur.execute(
                """
                INSERT INTO asset.quality_evaluation_items (
                    evaluation_id, candidate_id, recommendation, flags
                )
                VALUES (%s, %s, %s, %s::jsonb)
                """,
                (
                    evaluation_id,
                    item["candidate_id"],
                    item["recommendation"],
                    _json_dump(item["flags"]),
                ),
            )

    return {"evaluation_id": evaluation_id, "item_count": len(items)}


def create_export(
    conn,
    evaluation_id: int,
    created_by: int | None,
) -> dict:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT id FROM asset.quality_evaluations WHERE id = %s",
            (evaluation_id,),
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Evaluation not found")
        cur.execute(
            """
            INSERT INTO asset.quality_exports (evaluation_id, state, created_by)
            VALUES (%s, 'pending', %s)
            RETURNING id
            """,
            (evaluation_id, created_by),
        )
        export = cur.fetchone()
    return {"export_id": export["id"]}


def get_export(conn, export_id: int) -> dict:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, evaluation_id, state, storage_key, csv_filename, row_count,
                   file_sha256, error, created_at, updated_at
            FROM asset.quality_exports
            WHERE id = %s
            """,
            (export_id,),
        )
        export = cur.fetchone()
    if not export:
        raise HTTPException(status_code=404, detail="Export not found")
    return export


def get_evaluation(conn, evaluation_id: int) -> dict:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, batch_id, candidate_set_hash, filters,
                   profile_snapshots, status, created_by, created_at
            FROM asset.quality_evaluations
            WHERE id = %s
            """,
            (evaluation_id,),
        )
        evaluation = cur.fetchone()
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return evaluation


def export_path_for(export_id: int) -> Path:
    return ASSET_QUALITY_EXPORTS_DIR / f"quality-export-{export_id}.csv"

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from PIL import Image, ImageOps
from psycopg2.extras import RealDictCursor

from config import ASSET_QUALITY_PREVIEWS_DIR
from models.asset_quality import (
    CreateEvaluationRequest,
    EvaluatePreviewRequest,
    ProfileUpdateRequest,
    ReviewRequest,
)
from models.user import User
from services.asset_quality.evaluation_service import (
    create_evaluation,
    create_export,
    evaluate_preview,
    get_export,
    list_candidates,
)
from services.asset_quality.histograms import build_histograms_for_batch
from services.asset_quality.profiles import (
    METRIC_DEFINITIONS,
    ensure_default_profiles,
    get_profile_config,
)
from services.asset_quality.quality_service import create_quality_job
from services.auth import admin_required, get_current_active_user
from utils.db import db_connection, db_transaction


router = APIRouter(tags=["asset-quality"])


def _ensure_preview_dir() -> None:
    ASSET_QUALITY_PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)


def _candidate_preview_path(candidate_id: int, size: int) -> Path:
    filename = f"{candidate_id}.jpg" if size == 320 else f"{candidate_id}-{size}.jpg"
    return ASSET_QUALITY_PREVIEWS_DIR / filename


def _generate_candidate_preview(conn, candidate_id: int, size: int = 320) -> Path | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT source_path, decode_status
            FROM asset.quality_candidates
            WHERE id = %s
            """,
            (candidate_id,),
        )
        candidate = cur.fetchone()
    if not candidate or candidate["decode_status"] != "ok":
        return None

    source = Path(candidate["source_path"])
    if not source.exists():
        return None
    target = _candidate_preview_path(candidate_id, size)
    if target.exists() and target.stat().st_mtime_ns >= source.stat().st_mtime_ns:
        return target

    _ensure_preview_dir()
    temporary = target.with_name(f".{target.name}.{uuid4().hex}.part")
    try:
        with Image.open(source) as image:
            display_image = ImageOps.exif_transpose(image)
            display_image.thumbnail((size, size))
            if display_image.mode not in ("RGB", "L"):
                display_image = display_image.convert("RGB")
            display_image.save(temporary, format="JPEG", quality=90 if size > 320 else 85)
        temporary.replace(target)
        return target
    except Exception:
        if temporary.exists():
            temporary.unlink()
        return None


@router.post("/assets/imports/{batch_id}/quality/jobs")
async def create_quality_job_route(
    batch_id: int,
    current_user: User = Depends(admin_required),
):
    with db_transaction() as conn:
        result = create_quality_job(conn, batch_id, current_user.id)
    return result


@router.get("/assets/quality/jobs/{job_id}")
async def get_quality_job_route(
    job_id: int,
    current_user: User = Depends(get_current_active_user),
):
    with db_transaction() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT j.*, b.batch_name, b.image_path
                FROM asset.quality_jobs j
                JOIN asset.import_batches b ON b.id = j.batch_id
                WHERE j.id = %s
                """,
                (job_id,),
            )
            job = cur.fetchone()
            if not job:
                raise HTTPException(status_code=404, detail="Quality job not found")
            cur.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE status = 'completed') AS completed,
                    COUNT(*) FILTER (WHERE status = 'processing') AS processing,
                    COUNT(*) FILTER (WHERE status = 'failed') AS failed,
                    COUNT(*) FILTER (WHERE status = 'pending') AS pending
                FROM asset.quality_candidates
                WHERE batch_id = %s
                """,
                (job["batch_id"],),
            )
            job["candidate_progress"] = cur.fetchone()
    return job


@router.get("/assets/imports/{batch_id}/quality/metrics")
async def get_quality_metrics_route(
    batch_id: int,
    profile_key: str | None = None,
    current_user: User = Depends(get_current_active_user),
):
    with db_transaction() as conn:
        ensure_default_profiles(conn)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE status = 'completed') AS completed,
                    COUNT(*) FILTER (WHERE status = 'failed') AS failed,
                    COUNT(*) FILTER (WHERE status = 'pending') AS pending,
                    COUNT(*) FILTER (WHERE decode_status = 'failed') AS decode_failed
                FROM asset.quality_candidates
                WHERE batch_id = %s
                """,
                (batch_id,),
            )
            progress = cur.fetchone()
        histograms = build_histograms_for_batch(conn, batch_id, profile_key)
    return {
        "metric_definitions": METRIC_DEFINITIONS,
        "progress": progress,
        "histograms": histograms,
    }


@router.get("/assets/imports/{batch_id}/quality/histograms")
async def get_quality_histograms_route(
    batch_id: int,
    profile_key: str | None = None,
    current_user: User = Depends(get_current_active_user),
):
    with db_connection() as conn:
        return {"histograms": build_histograms_for_batch(conn, batch_id, profile_key)}


@router.post("/assets/imports/{batch_id}/quality/evaluate-preview")
async def evaluate_quality_preview_route(
    batch_id: int,
    payload: EvaluatePreviewRequest,
    current_user: User = Depends(get_current_active_user),
):
    with db_connection() as conn:
        return evaluate_preview(conn, batch_id, payload.model_dump())


@router.get("/assets/imports/{batch_id}/quality/candidates")
async def get_quality_candidates_route(
    batch_id: int,
    profile_key: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
):
    with db_connection() as conn:
        return list_candidates(conn, batch_id, page, page_size, profile_key)


@router.get("/assets/imports/{batch_id}/quality/near-duplicates")
async def get_near_duplicates_route(
    batch_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
):
    offset = (page - 1) * page_size
    with db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT COUNT(*) AS total
                FROM asset.quality_neighbor_pairs
                WHERE batch_id = %s
                """,
                (batch_id,),
            )
            total = cur.fetchone()["total"]
            cur.execute(
                """
                SELECT id, left_candidate_id, right_candidate_id,
                       right_image_id, phash_left, phash_right,
                       distance, scope, index_version
                FROM asset.quality_neighbor_pairs
                WHERE batch_id = %s
                ORDER BY distance, id
                LIMIT %s OFFSET %s
                """,
                (batch_id, page_size, offset),
            )
            pairs = cur.fetchall()
    return {"pairs": pairs, "total": total, "page": page, "page_size": page_size}


@router.get("/assets/quality/profiles")
async def get_quality_profiles_route(
    current_user: User = Depends(get_current_active_user),
):
    with db_transaction() as conn:
        ensure_default_profiles(conn)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT DISTINCT ON (profile_key)
                    id, profile_key, capture_type, spectral_type, bit_depth,
                    version, config, status, updated_at
                FROM asset.quality_profiles
                WHERE status = 'active'
                ORDER BY profile_key, version DESC
                """
            )
            profiles = cur.fetchall()
    return {"profiles": profiles}


@router.put("/assets/quality/profiles/{profile_id}")
async def update_quality_profile_route(
    profile_id: int,
    payload: ProfileUpdateRequest,
    current_user: User = Depends(admin_required),
):
    if not isinstance(payload.config, dict):
        raise HTTPException(status_code=400, detail="config must be an object")
    invalid_metrics = [
        key for key in payload.config.get("metrics", {}) if key not in METRIC_DEFINITIONS
    ]
    if invalid_metrics:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown metric ids: {', '.join(sorted(invalid_metrics))}",
        )

    with db_transaction() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT profile_key, capture_type, spectral_type, bit_depth, version
                FROM asset.quality_profiles
                WHERE id = %s
                """,
                (profile_id,),
            )
            current = cur.fetchone()
            if not current:
                raise HTTPException(status_code=404, detail="Profile not found")
            new_version = int(current["version"]) + 1
            import json

            cur.execute(
                """
                INSERT INTO asset.quality_profiles (
                    profile_key, capture_type, spectral_type, bit_depth,
                    version, config, status
                )
                VALUES (%s, %s, %s, %s, %s, %s::jsonb, 'active')
                RETURNING id, profile_key, version
                """,
                (
                    current["profile_key"],
                    current["capture_type"],
                    current["spectral_type"],
                    current["bit_depth"],
                    new_version,
                    json.dumps(payload.config, ensure_ascii=False),
                ),
            )
            new_profile = cur.fetchone()
            cur.execute(
                """
                UPDATE asset.quality_profiles
                SET status = 'disabled', updated_at = NOW()
                WHERE profile_key = %s AND status = 'active' AND id <> %s
                """,
                (current["profile_key"], new_profile["id"]),
            )
    return {"profile": new_profile}


@router.post("/assets/imports/{batch_id}/quality/evaluations")
async def create_quality_evaluation_route(
    batch_id: int,
    payload: CreateEvaluationRequest,
    current_user: User = Depends(admin_required),
):
    with db_transaction() as conn:
        return create_evaluation(conn, batch_id, payload.model_dump(), current_user.id)


@router.post("/assets/quality/reviews")
async def create_quality_review_route(
    payload: ReviewRequest,
    current_user: User = Depends(admin_required),
):
    with db_transaction() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO asset.quality_manual_reviews (
                    candidate_id, decision, note, reviewed_by
                )
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (
                    payload.candidate_id,
                    payload.decision,
                    payload.note,
                    current_user.id,
                ),
            )
            review = cur.fetchone()
    return {"review_id": review["id"]}


@router.post("/assets/quality/evaluations/{evaluation_id}/exports")
async def create_quality_export_route(
    evaluation_id: int,
    current_user: User = Depends(admin_required),
):
    with db_transaction() as conn:
        return create_export(conn, evaluation_id, current_user.id)


@router.get("/assets/quality/exports/{export_id}")
async def get_quality_export_route(
    export_id: int,
    current_user: User = Depends(get_current_active_user),
):
    with db_connection() as conn:
        return get_export(conn, export_id)


@router.get("/assets/quality/exports/{export_id}/download")
async def download_quality_export_route(
    export_id: int,
    current_user: User = Depends(get_current_active_user),
):
    with db_connection() as conn:
        export = get_export(conn, export_id)
    if export["state"] != "completed" or not export["storage_key"]:
        raise HTTPException(status_code=409, detail="Export is not ready")
    from config import ASSET_QUALITY_EXPORTS_DIR

    target = ASSET_QUALITY_EXPORTS_DIR / export["csv_filename"]
    if not target.exists():
        raise HTTPException(status_code=404, detail="Export file not found")
    return FileResponse(target, media_type="text/csv", filename=export["csv_filename"])


@router.get("/assets/quality/candidates/{candidate_id}/thumbnail")
async def get_quality_candidate_thumbnail_route(
    candidate_id: int,
    size: int = Query(320),
    current_user: User = Depends(get_current_active_user),
):
    if size not in (320, 1600):
        raise HTTPException(status_code=422, detail="size must be 320 or 1600")
    with db_connection() as conn:
        target = _generate_candidate_preview(conn, candidate_id, size)
    if not target or not target.exists():
        raise HTTPException(status_code=404, detail="Thumbnail not available")
    return FileResponse(target, media_type="image/jpeg")

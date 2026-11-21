from __future__ import annotations

import logging
from pathlib import Path

import imagehash
from PIL import Image, ImageOps
from psycopg2.extras import RealDictCursor

from config import ASSET_ORIGINALS_DIR, QUALITY_PHASH_SEARCH_RADIUS, QUALITY_PHASH_VERSION


logger = logging.getLogger("asset_quality.duplicates")


def _phash_to_hex(phash: imagehash.ImageHash | None) -> str:
    if phash is None:
        return "0" * 16
    return str(phash)


def _hex_to_int(value: str) -> int:
    return int(value or "0", 16)


def hamming_distance(left_hex: str, right_hex: str) -> int:
    return (_hex_to_int(left_hex) ^ _hex_to_int(right_hex)).bit_count()


def compute_phash(path: Path) -> str:
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source)
        if image.mode not in ("L", "RGB"):
            image = image.convert("RGB")
        return _phash_to_hex(imagehash.phash(image))


def ensure_library_phashes(conn) -> None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT im.id, im.storage_key
            FROM asset.images im
            LEFT JOIN asset.quality_library_phashes p ON p.image_id = im.id
            WHERE p.image_id IS NULL
            ORDER BY im.id
            """
        )
        rows = cur.fetchall()

    for row in rows:
        source = ASSET_ORIGINALS_DIR / row["storage_key"]
        if not source.exists():
            continue
        try:
            phash = compute_phash(source)
        except Exception as exc:
            logger.warning("Failed to compute library pHash for image %s: %s", row["id"], exc)
            continue
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO asset.quality_library_phashes (
                    image_id, phash_64, algorithm_version
                )
                VALUES (%s, %s, %s)
                ON CONFLICT (image_id) DO UPDATE
                SET phash_64 = EXCLUDED.phash_64,
                    algorithm_version = EXCLUDED.algorithm_version,
                    updated_at = NOW()
                """,
                (row["id"], phash, QUALITY_PHASH_VERSION),
            )


def _set_exact_duplicate(conn, candidate: dict) -> None:
    if not candidate["sha256"]:
        return

    scope = None
    existing_image_id = None
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT id FROM asset.images WHERE sha256 = %s LIMIT 1",
            (candidate["sha256"],),
        )
        library = cur.fetchone()
        if library:
            scope = "library"
            existing_image_id = library["id"]

        cur.execute(
            """
            SELECT id FROM asset.quality_candidates
            WHERE batch_id = %s AND sha256 = %s AND id < %s
            LIMIT 1
            """,
            (candidate["batch_id"], candidate["sha256"], candidate["id"]),
        )
        batch_match = cur.fetchone()
        if batch_match and existing_image_id:
            scope = "both"
        elif batch_match:
            scope = "batch"

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE asset.quality_candidates
            SET exact_duplicate = %s,
                duplicate_scope = %s,
                existing_image_id = %s,
                updated_at = NOW()
            WHERE id = %s
            """,
            (scope is not None, scope, existing_image_id, candidate["id"]),
        )


def detect_duplicates_for_batch(conn, batch_id: int) -> dict:
    ensure_library_phashes(conn)

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, batch_id, source_path, sha256, phash_64
            FROM asset.quality_candidates
            WHERE batch_id = %s
              AND decode_status = 'ok'
              AND status = 'completed'
            ORDER BY id
            """,
            (batch_id,),
        )
        candidates = cur.fetchall()

    for candidate in candidates:
        _set_exact_duplicate(conn, candidate)
        if not candidate["phash_64"] or candidate["phash_64"] == "0" * 16:
            try:
                candidate["phash_64"] = compute_phash(Path(candidate["source_path"]))
            except Exception:
                candidate["phash_64"] = "0" * 16
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE asset.quality_candidates SET phash_64 = %s WHERE id = %s",
                    (candidate["phash_64"], candidate["id"]),
                )

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT image_id, phash_64
            FROM asset.quality_library_phashes
            ORDER BY image_id
            """
        )
        library_phashes = cur.fetchall()

    # Clean previous pairs for this batch, then rebuild the nearest-neighbour
    # pairs within the currently covered search radius.
    with conn.cursor() as cur:
        cur.execute("DELETE FROM asset.quality_neighbor_pairs WHERE batch_id = %s", (batch_id,))

    batch_covered = 0
    library_covered = 0

    for candidate in candidates:
        nearest_batch = None
        nearest_batch_distance = QUALITY_PHASH_SEARCH_RADIUS + 1
        for other in candidates:
            if other["id"] == candidate["id"]:
                continue
            distance = hamming_distance(candidate["phash_64"], other["phash_64"])
            if distance < nearest_batch_distance:
                nearest_batch_distance = distance
                nearest_batch = other
        if nearest_batch:
            batch_covered += 1

        nearest_library = None
        nearest_library_distance = QUALITY_PHASH_SEARCH_RADIUS + 1
        for library in library_phashes:
            distance = hamming_distance(candidate["phash_64"], library["phash_64"])
            if distance < nearest_library_distance:
                nearest_library_distance = distance
                nearest_library = library
        if nearest_library:
            library_covered += 1

        with conn.cursor() as cur:
            if nearest_batch:
                cur.execute(
                    """
                    INSERT INTO asset.quality_neighbor_pairs (
                        batch_id, left_candidate_id, right_candidate_id,
                        right_image_id, phash_left, phash_right,
                        distance, scope, index_version
                    )
                    VALUES (%s, %s, %s, NULL, %s, %s, %s, 'batch', %s)
                    ON CONFLICT (batch_id, left_candidate_id, right_candidate_id,
                                 right_image_id, scope, index_version)
                    DO UPDATE SET distance = EXCLUDED.distance,
                                  phash_left = EXCLUDED.phash_left,
                                  phash_right = EXCLUDED.phash_right
                    """,
                    (
                        batch_id,
                        candidate["id"],
                        nearest_batch["id"],
                        candidate["phash_64"],
                        nearest_batch["phash_64"],
                        nearest_batch_distance,
                        QUALITY_PHASH_VERSION,
                    ),
                )
            if nearest_library:
                cur.execute(
                    """
                    INSERT INTO asset.quality_neighbor_pairs (
                        batch_id, left_candidate_id, right_candidate_id,
                        right_image_id, phash_left, phash_right,
                        distance, scope, index_version
                    )
                    VALUES (%s, %s, NULL, %s, %s, %s, %s, 'library', %s)
                    ON CONFLICT (batch_id, left_candidate_id, right_candidate_id,
                                 right_image_id, scope, index_version)
                    DO UPDATE SET distance = EXCLUDED.distance,
                                  phash_left = EXCLUDED.phash_left,
                                  phash_right = EXCLUDED.phash_right
                    """,
                    (
                        batch_id,
                        candidate["id"],
                        nearest_library["image_id"],
                        candidate["phash_64"],
                        nearest_library["phash_64"],
                        nearest_library_distance,
                        QUALITY_PHASH_VERSION,
                    ),
                )

            coverage = "complete" if nearest_batch or nearest_library else "partial"
            cur.execute(
                """
                UPDATE asset.quality_candidates
                SET phash_min_distance = LEAST(
                        COALESCE(phash_min_distance, 65),
                        LEAST(%s, %s)
                    ),
                    phash_nearest_candidate_id = %s,
                    phash_nearest_image_id = %s,
                    similarity_coverage = %s,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (
                    nearest_batch_distance if nearest_batch else 65,
                    nearest_library_distance if nearest_library else 65,
                    nearest_batch["id"] if nearest_batch else None,
                    nearest_library["image_id"] if nearest_library else None,
                    coverage,
                    candidate["id"],
                ),
            )

    return {
        "batch_covered": batch_covered,
        "library_covered": library_covered,
        "search_radius": QUALITY_PHASH_SEARCH_RADIUS,
    }

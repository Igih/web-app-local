from __future__ import annotations

import math

from psycopg2.extras import RealDictCursor

from services.asset_quality.profiles import METRIC_DEFINITIONS


HISTOGRAM_BINS = 48


def _histogram(values: list[float], bins: int = HISTOGRAM_BINS) -> dict:
    if not values:
        return {"edges": [], "counts": []}

    minimum = min(values)
    maximum = max(values)
    if not math.isfinite(minimum) or not math.isfinite(maximum):
        return {"edges": [], "counts": []}
    if maximum <= minimum:
        maximum = minimum + 1.0

    step = (maximum - minimum) / bins
    edges = [minimum + step * index for index in range(bins + 1)]
    counts = [0] * bins
    for value in values:
        index = min(bins - 1, int((value - minimum) / step))
        counts[index] += 1
    return {"edges": edges, "counts": counts}


def _profile_filter_sql(profile_key: str | None) -> tuple[str, list[object]]:
    if not profile_key:
        return "1 = 1", []
    return "c.profile_key = %s", [profile_key]


def build_histograms_for_batch(
    conn,
    batch_id: int,
    profile_key: str | None = None,
) -> list[dict]:
    where_sql, params = _profile_filter_sql(profile_key)
    params = [batch_id, *params]
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""
            SELECT c.id AS candidate_id, c.profile_key, m.*
            FROM asset.quality_candidates c
            JOIN LATERAL (
                SELECT * FROM asset.quality_metric_results m
                WHERE m.candidate_id = c.id
                ORDER BY m.id DESC
                LIMIT 1
            ) m ON TRUE
            WHERE c.batch_id = %s
              AND c.decode_status = 'ok'
              AND c.status = 'completed'
              AND {where_sql}
            ORDER BY c.id
            """,
            params,
        )
        rows = cur.fetchall()

    result = []
    for metric_id, definition in METRIC_DEFINITIONS.items():
        values = []
        missing_count = 0
        for row in rows:
            value = row.get(metric_id)
            if value is None:
                missing_count += 1
            else:
                values.append(float(value))

        result.append(
            {
                "metric_id": metric_id,
                "display_name": definition["display_name"],
                "direction": definition["direction"],
                "unit": definition["unit"],
                "histogram": _histogram(values),
                "missing_count": missing_count,
                "value_count": len(values),
            }
        )
    return result

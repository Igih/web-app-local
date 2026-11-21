from __future__ import annotations

from psycopg2.extras import RealDictCursor


METRIC_DEFINITIONS = {
    "blur_effect": {
        "display_name": "模糊度",
        "direction": "high",
        "unit": "0~1",
        "numeric": True,
    },
    "rms_contrast": {
        "display_name": "RMS 对比度",
        "direction": "low",
        "unit": "0~1",
        "numeric": True,
    },
    "noise_sigma": {
        "display_name": "噪声估计",
        "direction": "high",
        "unit": "sigma",
        "numeric": True,
    },
    "bright_fraction": {
        "display_name": "过曝比例",
        "direction": "high",
        "unit": "0~1",
        "numeric": True,
    },
}


def _metric_config(metric_id: str) -> dict:
    if metric_id == "blur_effect":
        return {"enabled": True, "direction": "high", "review": 0.55, "severe": 0.85, "severe_enabled": False}
    if metric_id == "rms_contrast":
        return {"enabled": True, "direction": "low", "review": 0.08, "severe": 0.03, "severe_enabled": False}
    if metric_id == "bright_fraction":
        return {"enabled": True, "direction": "high", "review": 0.20, "severe": 0.50, "severe_enabled": False}
    if metric_id == "noise_sigma":
        return {"enabled": True, "direction": "high", "review": 20.0, "severe": 50.0, "severe_enabled": False}
    raise ValueError(f"unknown metric: {metric_id}")


def build_default_profile_config() -> dict:
    return {
        "preprocess_version": "preprocess_v1",
        "missing_metric_policy": "review",
        "exact_duplicate_policy": "skip_new_file_keep_source",
        "near_duplicate_policy": "review",
        "metrics": {
            metric_id: _metric_config(metric_id)
            for metric_id in METRIC_DEFINITIONS
        },
    }


PROFILE_BASENAMES = {
    "photo_visible": ("photo", "visible"),
    "photo_infrared": ("photo", "infrared"),
    "hand_drawn_visible": ("hand_drawn", "visible"),
    "hand_drawn_infrared": ("hand_drawn", "infrared"),
    "unspecified": (None, None),
}


def default_profiles() -> list[dict]:
    profiles = []
    for key, (capture_type, spectral_type) in PROFILE_BASENAMES.items():
        for bit_depth in (8,):
            profile_key = f"{key}_{bit_depth}bit" if key != "unspecified" else key
            profiles.append(
                {
                    "profile_key": profile_key,
                    "capture_type": capture_type,
                    "spectral_type": spectral_type,
                    "bit_depth": bit_depth,
                    "version": 1,
                    "config": build_default_profile_config(),
                    "status": "active",
                }
            )
    return profiles


def ensure_default_profiles(conn) -> None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        for profile in default_profiles():
            cur.execute(
                """
                SELECT id FROM asset.quality_profiles
                WHERE profile_key = %s AND version = %s
                """,
                (profile["profile_key"], profile["version"]),
            )
            if cur.fetchone():
                continue
            cur.execute(
                """
                INSERT INTO asset.quality_profiles (
                    profile_key, capture_type, spectral_type, bit_depth,
                    version, config, status
                )
                VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s)
                """,
                (
                    profile["profile_key"],
                    profile["capture_type"],
                    profile["spectral_type"],
                    profile["bit_depth"],
                    profile["version"],
                    _json(profile["config"]),
                    profile["status"],
                ),
            )


def _json(value: dict) -> str:
    import json

    return json.dumps(value, ensure_ascii=False)


def get_profile_config(conn, profile_key: str) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT config, version
            FROM asset.quality_profiles
            WHERE profile_key = %s
            ORDER BY version DESC
            LIMIT 1
            """,
            (profile_key,),
        )
        row = cur.fetchone()
    if not row:
        return None
    return {"config": row["config"], "version": row["version"]}

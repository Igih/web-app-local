import numpy as np
import pytest

from services.asset_quality import evaluation_service
from services.asset_quality.image_decoder import (
    decode_for_analysis,
    profile_key_for_candidate,
)
from services.asset_quality.metrics import calculate_metrics
from services.asset_quality.profiles import build_default_profile_config
from services.asset_quality.quality_rule_engine import recommend_candidate


def _config_with_rule(metric_id: str, rule: dict) -> dict:
    config = build_default_profile_config()
    config["metrics"][metric_id] = rule
    return config


def test_profile_key_for_candidate() -> None:
    assert profile_key_for_candidate("photo", "visible", 8) == "photo_visible_8bit"
    assert profile_key_for_candidate("hand_drawn", "infrared", 16) == "hand_drawn_infrared_16bit"
    assert profile_key_for_candidate(None, "infrared", 8) == "unspecified"


def test_high_metric_boundaries() -> None:
    config = _config_with_rule(
        "blur_effect",
        {"enabled": True, "direction": "high", "review": 0.5, "severe": 0.8, "severe_enabled": True},
    )
    assert recommend_candidate(
        decode_status="ok",
        metrics={"blur_effect": 0.5},
        profile_config=config,
    )[0] == "review"
    assert recommend_candidate(
        decode_status="ok",
        metrics={"blur_effect": 0.8},
        profile_config=config,
    )[0] == "exclude"


def test_low_metric_boundaries() -> None:
    config = _config_with_rule(
        "rms_contrast",
        {"enabled": True, "direction": "low", "review": 0.08, "severe": 0.03, "severe_enabled": False},
    )
    assert recommend_candidate(
        decode_status="ok",
        metrics={"rms_contrast": 0.03},
        profile_config=config,
    )[0] == "review"


def test_removed_metric_does_not_affect_recommendation() -> None:
    config = build_default_profile_config()
    for rule in config["metrics"].values():
        rule["enabled"] = False
    config["metrics"]["entropy_8bit"] = {
        "enabled": True, "direction": "low", "review": 4, "severe": 2,
    }
    recommendation, flags = recommend_candidate(
        decode_status="ok",
        metrics={"entropy_8bit": 0},
        profile_config=config,
    )
    assert (recommendation, flags) == ("admit", [])


def test_decode_failed_excludes() -> None:
    config = build_default_profile_config()
    recommendation, flags = recommend_candidate(
        decode_status="failed",
        metrics={},
        profile_config=config,
    )
    assert recommendation == "exclude"
    assert "DECODE_FAILED" in flags


def test_exact_duplicate_excludes() -> None:
    config = build_default_profile_config()
    recommendation, flags = recommend_candidate(
        decode_status="ok",
        metrics={},
        profile_config=config,
        exact_duplicate=True,
    )
    assert recommendation == "exclude"
    assert "EXACT_DUPLICATE" in flags


def test_exact_duplicate_excludes_with_all_quality_metrics_disabled() -> None:
    config = build_default_profile_config()
    for rule in config["metrics"].values():
        rule["enabled"] = False
    recommendation, flags = recommend_candidate(
        decode_status="ok",
        metrics={},
        profile_config=config,
        exact_duplicate=True,
    )
    assert (recommendation, flags) == ("exclude", ["EXACT_DUPLICATE"])


def test_metrics_on_constant_image() -> None:
    image = np.full((64, 64, 3), 128, dtype=np.uint8)
    decoded = {
        "array": image,
        "gray_u8": np.full((64, 64), 128, dtype=np.uint8),
        "bit_depth": 8,
    }
    metrics = calculate_metrics(decoded, image.dtype)
    assert metrics["rms_contrast"] == pytest.approx(0.0, abs=1e-6)
    assert metrics["bright_fraction"] == 0.0
    assert set(metrics).isdisjoint({"entropy_8bit", "lap_var", "tenengrad"})


def test_preview_filters_before_pagination(monkeypatch) -> None:
    rows = [{"candidate_id": candidate_id} for candidate_id in range(1, 6)]
    monkeypatch.setattr(evaluation_service, "_load_candidate_rows", lambda *args: rows)
    monkeypatch.setattr(evaluation_service, "_profile_for_candidate", lambda *args: ({}, None))
    monkeypatch.setattr(evaluation_service, "_merge_profile_config", lambda config, rules: config)
    monkeypatch.setattr(
        evaluation_service,
        "_evaluate_row",
        lambda conn, row, config: (
            "exclude" if row["candidate_id"] % 2 == 0 else "review", []
        ),
    )
    monkeypatch.setattr(
        evaluation_service,
        "_candidate_item",
        lambda row, recommendation, flags: {"candidate_id": row["candidate_id"]},
    )

    result = evaluation_service.evaluate_preview(
        None,
        1,
        {"recommendation_filter": "exclude", "page": 2, "page_size": 1},
    )

    assert result["counts"] == {"admit": 0, "review": 3, "exclude": 2}
    assert result["candidate_total"] == 2
    assert result["candidate_items"] == [{"candidate_id": 4}]
    assert result["page"] == 2

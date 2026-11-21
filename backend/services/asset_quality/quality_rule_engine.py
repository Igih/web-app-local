from __future__ import annotations

from services.asset_quality.profiles import METRIC_DEFINITIONS


FLAG_BY_METRIC = {
    "blur_effect": "BLUR_SUSPECT",
    "rms_contrast": "LOW_CONTRAST",
    "bright_fraction": "HIGHLIGHT_CLIPPING",
    "noise_sigma": "HIGH_NOISE",
}


def _score_metric(metric_id: str, value: float | None, rule: dict) -> str:
    if not rule.get("enabled", False):
        return "disabled"
    if value is None:
        return "missing"

    direction = rule.get("direction")
    if direction == "high":
        if value >= float(rule.get("severe", 1.0)):
            return "severe"
        if value >= float(rule.get("review", 0.0)):
            return "warn"
        return "ok"

    if direction == "low":
        if value <= float(rule.get("severe", 0.0)):
            return "severe"
        if value <= float(rule.get("review", 1.0)):
            return "warn"
        return "ok"

    return "disabled"


def evaluate_metric_rules(metrics: dict, profile_config: dict) -> list[tuple[str, str]]:
    """Return [(level, flag_code)] for all enabled metric rules."""
    rules = profile_config.get("metrics", {})
    results: list[tuple[str, str]] = []

    for metric_id, definition in METRIC_DEFINITIONS.items():
        rule = rules.get(metric_id, {})
        score = _score_metric(metric_id, metrics.get(metric_id), rule)
        if score in {"warn", "severe"}:
            flag_code = FLAG_BY_METRIC.get(metric_id, metric_id.upper())
            results.append((score, flag_code))
    return results


def recommend_candidate(
    *,
    decode_status: str,
    metrics: dict,
    profile_config: dict,
    exact_duplicate: bool = False,
    source_changed: bool = False,
) -> tuple[str, list[str]]:
    """Return a single recommendation and all explanatory flag codes."""
    if decode_status != "ok":
        return "exclude", ["DECODE_FAILED"]

    if exact_duplicate:
        return "exclude", ["EXACT_DUPLICATE"]

    metric_results = evaluate_metric_rules(metrics, profile_config)
    flags = [flag for _, flag in metric_results]

    if source_changed:
        flags.append("SOURCE_CHANGED")

    has_enabled_severe = any(
        level == "severe"
        and metric_severity_enabled(metric_id, profile_config)
        for metric_id in METRIC_DEFINITIONS
        for level, _ in [score_for(metric_id, metrics, profile_config)]
    )
    if has_enabled_severe:
        return "exclude", flags

    if flags:
        return "review", flags

    missing_policy = profile_config.get("missing_metric_policy", "review")
    if missing_policy == "review":
        required_missing = [
            metric_id
            for metric_id in METRIC_DEFINITIONS
            if metrics.get(metric_id) is None
            and profile_config.get("metrics", {}).get(metric_id, {}).get("enabled", False)
        ]
        if required_missing:
            flags.append("METRIC_UNAVAILABLE")
            return "review", flags

    return "admit", []


def score_for(metric_id: str, metrics: dict, profile_config: dict) -> tuple[str, str | None]:
    rule = profile_config.get("metrics", {}).get(metric_id, {})
    return _score_metric(metric_id, metrics.get(metric_id), rule), None


def metric_severity_enabled(metric_id: str, profile_config: dict) -> bool:
    rule = profile_config.get("metrics", {}).get(metric_id, {})
    return bool(rule.get("enabled", False) and rule.get("severe_enabled", False))

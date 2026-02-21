#!/usr/bin/env python3
"""Stress extraction and proxy-derivation helpers for reports."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional


DIRECT_STRESS_SCORE_KEYS = (
    "stress_score",
    "stress",
    "average_stress",
    "average_stress_level",
    "stress_level",
)

DIRECT_STRESS_STATUS_KEYS = (
    "day_summary",
    "status",
    "stress_status",
)

STATUS_TO_SCORE = {
    "restored": 25.0,
    "relaxed": 30.0,
    "normal": 50.0,
    "engaged": 60.0,
    "stressed": 75.0,
    "high_stress": 85.0,
    "overstressed": 90.0,
}

# Contributor keys are usually 0-100 where higher means better recovery.
READINESS_STRESS_CONTRIBUTOR_KEYS = (
    "hrv_balance",
    "resting_heart_rate",
    "recovery_index",
    "sleep_balance",
    "previous_night",
)


def _clamp_0_100(value: float) -> float:
    return max(0.0, min(100.0, value))


def _to_score(value: Any) -> Optional[float]:
    """Coerce numeric values to a stress score in [0, 100]."""
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return round(_clamp_0_100(parsed), 1)


def _iter_records(*records: Optional[Dict[str, Any]]) -> Iterable[Dict[str, Any]]:
    for record in records:
        if isinstance(record, dict):
            yield record


def extract_direct_stress_score(*records: Optional[Dict[str, Any]]) -> Optional[float]:
    """Extract direct stress score from known keys/status fields, if present."""
    for record in _iter_records(*records):
        for key in DIRECT_STRESS_SCORE_KEYS:
            if key in record:
                score = _to_score(record.get(key))
                if score is not None:
                    return score

        for key in DIRECT_STRESS_STATUS_KEYS:
            value = record.get(key)
            if isinstance(value, str):
                mapped = STATUS_TO_SCORE.get(value.strip().lower())
                if mapped is not None:
                    return mapped

    return None


def _derive_proxy_stress_score(
    sleep_record: Optional[Dict[str, Any]],
    readiness_record: Optional[Dict[str, Any]],
    baseline_hrv: float,
    baseline_rhr: float,
) -> Dict[str, Any]:
    """Derive stress proxy from sleep/readiness signals when direct fields are missing."""
    components: List[float] = []
    component_names: List[str] = []

    sleep = sleep_record or {}
    readiness = readiness_record or {}

    # HRV lower than baseline implies higher stress load.
    hrv = sleep.get("average_hrv")
    if hrv is not None and baseline_hrv > 0:
        hrv_component = 50 + ((baseline_hrv - float(hrv)) / baseline_hrv) * 50
        components.append(_clamp_0_100(hrv_component))
        component_names.append("hrv")

    # RHR higher than baseline implies higher stress load.
    rhr = sleep.get("lowest_heart_rate")
    if rhr is not None and baseline_rhr > 0:
        rhr_component = 50 + ((float(rhr) - baseline_rhr) / baseline_rhr) * 50
        components.append(_clamp_0_100(rhr_component))
        component_names.append("resting_hr")

    contributors = readiness.get("contributors", {}) if isinstance(readiness.get("contributors"), dict) else {}

    for key in READINESS_STRESS_CONTRIBUTOR_KEYS:
        value = contributors.get(key)
        if value is None:
            value = readiness.get(key)
        numeric = _to_score(value)
        if numeric is not None:
            # Invert recovery-style score (high contributor = lower stress).
            components.append(_clamp_0_100(100 - numeric))
            component_names.append(key)

    efficiency = _to_score(sleep.get("efficiency"))
    if efficiency is not None:
        components.append(_clamp_0_100(100 - efficiency))
        component_names.append("sleep_efficiency")

    if not components:
        return {
            "score": None,
            "components": [],
            "reason": "insufficient signals",
        }

    score = round(sum(components) / len(components), 1)
    return {
        "score": score,
        "components": component_names,
        "reason": "derived from HRV/RHR/readiness contributors",
    }


def stress_status(score: Optional[float]) -> str:
    if score is None:
        return "UNKNOWN"
    if score <= 40:
        return "LOW"
    if score <= 65:
        return "MODERATE"
    return "HIGH"


def stress_trend_direction(delta: Optional[float]) -> str:
    if delta is None:
        return "unknown"
    if delta > 2:
        return "up"
    if delta < -2:
        return "down"
    return "stable"


def build_stress_day(
    day: str,
    sleep_record: Optional[Dict[str, Any]] = None,
    readiness_record: Optional[Dict[str, Any]] = None,
    stress_record: Optional[Dict[str, Any]] = None,
    baseline_hrv: float = 40.0,
    baseline_rhr: float = 60.0,
) -> Dict[str, Any]:
    """Build normalized stress data for one day from direct or derived sources."""
    direct = extract_direct_stress_score(stress_record, readiness_record, sleep_record)
    if direct is not None:
        return {
            "day": day,
            "score": direct,
            "status": stress_status(direct),
            "source": "direct",
            "derived": False,
            "components": [],
            "label": "direct stress",
        }

    proxy = _derive_proxy_stress_score(sleep_record, readiness_record, baseline_hrv, baseline_rhr)
    score = proxy["score"]
    return {
        "day": day,
        "score": score,
        "status": stress_status(score),
        "source": "derived" if score is not None else "unavailable",
        "derived": score is not None,
        "components": proxy.get("components", []),
        "label": proxy.get("reason", "derived proxy"),
    }


def summarize_weekly_stress(
    sleep_data: List[Dict[str, Any]],
    readiness_data: Optional[List[Dict[str, Any]]] = None,
    stress_data: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Compute weekly stress summary from available direct/derived data."""
    readiness_by_day = {r.get("day"): r for r in (readiness_data or []) if isinstance(r, dict)}
    stress_by_day = {s.get("day"): s for s in (stress_data or []) if isinstance(s, dict)}

    hrv_values = [float(s.get("average_hrv")) for s in sleep_data if s.get("average_hrv") is not None]
    rhr_values = [float(s.get("lowest_heart_rate")) for s in sleep_data if s.get("lowest_heart_rate") is not None]
    baseline_hrv = (sum(hrv_values) / len(hrv_values)) if hrv_values else 40.0
    baseline_rhr = (sum(rhr_values) / len(rhr_values)) if rhr_values else 60.0

    days: List[Dict[str, Any]] = []
    for sleep_day in sleep_data:
        day = sleep_day.get("day")
        if not day:
            continue
        days.append(build_stress_day(
            day=day,
            sleep_record=sleep_day,
            readiness_record=readiness_by_day.get(day),
            stress_record=stress_by_day.get(day),
            baseline_hrv=baseline_hrv,
            baseline_rhr=baseline_rhr,
        ))

    valid_days = [d for d in days if d.get("score") is not None]
    if not valid_days:
        return {
            "avg": None,
            "status": "UNKNOWN",
            "best_day": None,
            "worst_day": None,
            "trend": None,
            "trend_direction": "unknown",
            "days_tracked": 0,
            "derived_days": 0,
            "direct_days": 0,
            "days": days,
        }

    scores = [float(d["score"]) for d in valid_days]
    avg = round(sum(scores) / len(scores), 1)

    half = len(scores) // 2
    if half >= 1:
        first_half_avg = sum(scores[:half]) / half
        second_half_avg = sum(scores[half:]) / (len(scores) - half)
        trend = round(second_half_avg - first_half_avg, 1)
    else:
        trend = 0.0

    best = min(valid_days, key=lambda d: d["score"])  # lower stress is better
    worst = max(valid_days, key=lambda d: d["score"])  # higher stress is worse

    derived_days = len([d for d in valid_days if d.get("source") == "derived"])
    direct_days = len([d for d in valid_days if d.get("source") == "direct"])

    return {
        "avg": avg,
        "status": stress_status(avg),
        "best_day": best.get("day"),
        "worst_day": worst.get("day"),
        "trend": trend,
        "trend_direction": stress_trend_direction(trend),
        "days_tracked": len(valid_days),
        "derived_days": derived_days,
        "direct_days": direct_days,
        "days": valid_days,
    }


def calculate_stress_baseline(
    sleep_data: List[Dict[str, Any]],
    readiness_data: Optional[List[Dict[str, Any]]] = None,
    stress_data: Optional[List[Dict[str, Any]]] = None,
) -> Optional[float]:
    """Calculate average baseline stress from historical direct/derived signals."""
    summary = summarize_weekly_stress(sleep_data, readiness_data, stress_data)
    return summary.get("avg")

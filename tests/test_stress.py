#!/usr/bin/env python3
"""Tests for stress extraction and fallback derivation."""

import json
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from stress import (
    extract_direct_stress_score,
    build_stress_day,
    summarize_weekly_stress,
    calculate_stress_baseline,
)


FIXTURES = Path(__file__).resolve().parent / "fixtures"


def load_json(name):
    with open(FIXTURES / name, "r", encoding="utf-8") as f:
        return json.load(f)


def test_extract_direct_stress_score_from_explicit_field():
    record = {"day": "2026-01-15", "stress_score": 64}
    assert extract_direct_stress_score(record) == 64.0


def test_extract_direct_stress_score_from_status_label():
    record = {"day": "2026-01-15", "day_summary": "restored"}
    assert extract_direct_stress_score(record) == 25.0


def test_build_stress_day_prefers_direct_data():
    day = build_stress_day(
        day="2026-01-15",
        sleep_record={"average_hrv": 30, "lowest_heart_rate": 64, "efficiency": 80},
        readiness_record={"contributors": {"hrv_balance": 50}},
        stress_record={"stress_score": 72},
        baseline_hrv=40,
        baseline_rhr=60,
    )

    assert day["score"] == 72.0
    assert day["source"] == "direct"
    assert day["derived"] is False


def test_build_stress_day_uses_derived_proxy_when_direct_missing():
    inputs = load_json("stress_proxy_inputs.json")
    sleep = inputs["sleep"][0]
    readiness = inputs["readiness"][0]

    day = build_stress_day(
        day=sleep["day"],
        sleep_record=sleep,
        readiness_record=readiness,
        stress_record=None,
        baseline_hrv=40,
        baseline_rhr=60,
    )

    assert day["score"] is not None
    assert 0 <= day["score"] <= 100
    assert day["source"] == "derived"
    assert day["derived"] is True
    assert "hrv" in day["components"]


def test_summarize_weekly_stress_best_and_worst_day_from_direct_data():
    stress_data = load_json("stress_direct_response.json")
    sleep_data = [
        {"day": d["day"], "efficiency": 85, "total_sleep_duration": 25200}
        for d in stress_data
    ]

    summary = summarize_weekly_stress(sleep_data, readiness_data=[], stress_data=stress_data)

    assert summary["avg"] is not None
    assert summary["best_day"] == "2026-01-16"  # lowest stress score
    assert summary["worst_day"] == "2026-01-17"  # highest stress score
    assert summary["direct_days"] == 3
    assert summary["derived_days"] == 0


def test_calculate_stress_baseline_returns_none_with_no_signals():
    sleep = [{"day": "2026-01-15"}, {"day": "2026-01-16"}]
    baseline = calculate_stress_baseline(sleep, readiness_data=[], stress_data=[])

    assert baseline is None

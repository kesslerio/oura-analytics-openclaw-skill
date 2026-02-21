#!/usr/bin/env python3
"""Tests for weekly report stress summary integration."""

from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from weekly_report import analyze_week


def test_analyze_week_includes_stress_summary_from_direct_data():
    sleep = [
        {"day": "2026-01-15", "efficiency": 89, "total_sleep_duration": 25200},
        {"day": "2026-01-16", "efficiency": 85, "total_sleep_duration": 23400},
        {"day": "2026-01-17", "efficiency": 92, "total_sleep_duration": 27000},
    ]
    readiness = [
        {"day": "2026-01-15", "score": 75},
        {"day": "2026-01-16", "score": 68},
        {"day": "2026-01-17", "score": 80},
    ]
    stress = [
        {"day": "2026-01-15", "stress_score": 60},
        {"day": "2026-01-16", "stress_score": 45},
        {"day": "2026-01-17", "stress_score": 70},
    ]

    summary = analyze_week(sleep, readiness, stress)
    stress_summary = summary["stress_summary"]

    assert stress_summary["avg"] == 58.3
    assert stress_summary["best_day"] == "2026-01-16"
    assert stress_summary["worst_day"] == "2026-01-17"


def test_analyze_week_stress_summary_falls_back_to_derived_when_needed():
    sleep = [
        {"day": "2026-01-15", "average_hrv": 28, "lowest_heart_rate": 64, "efficiency": 80, "total_sleep_duration": 23000},
        {"day": "2026-01-16", "average_hrv": 45, "lowest_heart_rate": 56, "efficiency": 90, "total_sleep_duration": 27000},
    ]
    readiness = [
        {"day": "2026-01-15", "score": 70, "contributors": {"hrv_balance": 60, "resting_heart_rate": 58}},
        {"day": "2026-01-16", "score": 80, "contributors": {"hrv_balance": 85, "resting_heart_rate": 82}},
    ]

    summary = analyze_week(sleep, readiness, stress_data=[])
    stress_summary = summary["stress_summary"]

    assert stress_summary["avg"] is not None
    assert stress_summary["derived_days"] == 2
    assert stress_summary["direct_days"] == 0

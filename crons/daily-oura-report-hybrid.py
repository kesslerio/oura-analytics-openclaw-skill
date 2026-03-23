#!/usr/bin/env python3
"""
Daily Oura Health Report - Hybrid Format

Combines detailed metrics with driver analysis and sends via Telegram.
This is the main daily morning briefing script.
"""

import os
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# Add oura-analytics scripts directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from oura_api import OuraClient
from drivers import DriverAnalyzer, format_drivers_report
from baseline import build_baseline


def format_hours(seconds: int) -> str:
    """Format seconds as hours and minutes."""
    if not seconds:
        return "N/A"
    hours = seconds / 3600
    h = int(hours)
    m = int((hours - h) * 60)
    return f"{h}h {m}m"


def generate_report(date_str: str = None, baseline_days: int = 30) -> str:
    """Generate the daily Oura health report."""
    
    # Default to today (Oura labels sleep by the day you wake up)
    if date_str:
        target_date = date_str
    else:
        target_date = datetime.now().strftime("%Y-%m-%d")
    
    # Get Oura token
    token = os.environ.get("OURA_API_TOKEN")
    if not token:
        return "❌ Error: OURA_API_TOKEN not set"
    
    client = OuraClient(token, use_cache=False)
    
    # Fetch target day data
    # Note: Oura API filters by bedtime_start, not day field
    # So we query a range to catch sleep starting the night before
    # Using 2-day lookback to handle timezone edge cases (travel, DST)
    # Note: Oura API end_date is EXCLUSIVE, so add 1 day to include target
    target_dt = datetime.strptime(target_date, "%Y-%m-%d")
    range_start = (target_dt - timedelta(days=2)).strftime("%Y-%m-%d")
    range_end = (target_dt + timedelta(days=1)).strftime("%Y-%m-%d")
    sleep_data = client.get_sleep(range_start, range_end)
    readiness_data = client.get_readiness(range_start, range_end)
    
    # Filter to get records for our target day
    # Note: day field comparison assumes Oura account timezone matches report timezone
    sleep_for_day = [s for s in sleep_data if s.get("day") == target_date]
    readiness_for_day = [r for r in readiness_data if r.get("day") == target_date]
    
    if not sleep_for_day:
        return f"📭 No sleep data available for {target_date}"
    
    # Prefer "long_sleep" (main sleep) over naps; fallback to longest duration
    main_sleeps = [s for s in sleep_for_day if s.get("type") == "long_sleep"]
    if main_sleeps:
        sleep = max(main_sleeps, key=lambda s: s.get("total_sleep_duration", 0))
    else:
        # No long_sleep found, pick longest duration record
        sleep = max(sleep_for_day, key=lambda s: s.get("total_sleep_duration", 0))
    
    readiness = readiness_for_day[0] if readiness_for_day else {}
    
    # Fetch baseline data
    baseline_end = datetime.strptime(target_date, "%Y-%m-%d") - timedelta(days=1)
    baseline_start = baseline_end - timedelta(days=baseline_days)
    
    baseline_sleep = client.get_sleep(
        baseline_start.strftime("%Y-%m-%d"),
        baseline_end.strftime("%Y-%m-%d")
    )
    baseline_readiness = client.get_readiness(
        baseline_start.strftime("%Y-%m-%d"),
        baseline_end.strftime("%Y-%m-%d")
    )
    
    # Calculate baseline metrics
    baseline = build_baseline(baseline_sleep, baseline_readiness, baseline_days)
    
    # Build baseline dict for driver analyzer
    baseline_dict = {
        "sleep_hours": baseline.sleep_hours.mean if baseline.sleep_hours else 7.5,
        "efficiency": baseline.efficiency.mean if baseline.efficiency else 85.0,
        "deep_sleep": 1.5,
        "rem_sleep": 1.8,
        "hrv": baseline.hrv.mean if baseline.hrv else 40.0,
        "rhr": baseline.rhr.mean if baseline.rhr else 60.0,
        "readiness": baseline.readiness.mean if baseline.readiness else 75.0
    }
    
    analyzer = DriverAnalyzer(baseline_dict)
    
    # Analyze drivers
    sleep_drivers = analyzer.analyze_sleep_drivers(sleep)
    readiness_drivers = analyzer.analyze_readiness_drivers(sleep, readiness)
    
    readiness_score = readiness.get("score", 0) if readiness else 0
    suggestion = analyzer.generate_suggestion(readiness_score, readiness_drivers)
    
    # Build the report
    lines = []
    lines.append(f"📊 *Daily Oura Report - {target_date}*")
    lines.append("━" * 30)
    
    # Readiness (lead with most important metric)
    if readiness_score:
        baseline_ready = baseline.readiness.mean if baseline.readiness else 75.0
        delta_ready = readiness_score - baseline_ready
        delta_str = f"+{delta_ready:.0f}" if delta_ready > 0 else f"{delta_ready:.0f}"
        
        if readiness_score >= 85:
            emoji = "🟢"
        elif readiness_score >= 70:
            emoji = "🟡"
        else:
            emoji = "🔴"
        
        lines.append(f"\n{emoji} *Readiness: {readiness_score}/100* ({delta_str} vs baseline)")
        
        # Show negative drivers
        negative_drivers = [d for d in readiness_drivers if d.impact == "negative"]
        if negative_drivers:
            lines.append("   └─ *Factors pulling down:*")
            for driver in negative_drivers[:3]:
                lines.append(f"      • {driver.metric}: {driver.value:.0f} (baseline: {driver.baseline:.0f})")
    
    # Sleep metrics
    duration = sleep.get("total_sleep_duration")
    efficiency = sleep.get("efficiency")
    
    if duration:
        baseline_dur = baseline.sleep_hours.mean if baseline.sleep_hours else 7.5
        actual_dur = duration / 3600
        delta_dur = actual_dur - baseline_dur
        delta_str = f"+{delta_dur:.1f}h" if delta_dur > 0 else f"{delta_dur:.1f}h"
        
        lines.append(f"\n🌙 *Sleep: {format_hours(duration)}* ({delta_str} vs baseline)")
    
    if efficiency:
        baseline_eff = baseline.efficiency.mean if baseline.efficiency else 85.0
        delta_eff = efficiency - baseline_eff
        delta_str = f"+{delta_eff:.0f}%" if delta_eff > 0 else f"{delta_eff:.0f}%"
        
        lines.append(f"   Efficiency: {efficiency}% ({delta_str})")
    
    # Sleep stages
    deep = sleep.get("deep_sleep_duration")
    rem = sleep.get("rem_sleep_duration")
    light = sleep.get("light_sleep_duration")
    
    if deep or rem or light:
        lines.append("\n   *Sleep Stages:*")
        if deep:
            lines.append(f"      🌊 Deep: {format_hours(deep)}")
        if light:
            lines.append(f"      💡 Light: {format_hours(light)}")
        if rem:
            lines.append(f"      🧠 REM: {format_hours(rem)}")
    
    # HRV & RHR
    hrv = sleep.get("average_hrv")
    rhr = sleep.get("lowest_heart_rate")
    
    if hrv or rhr:
        lines.append("\n   *Recovery Markers:*")
        if hrv:
            baseline_hrv = baseline.hrv.mean if baseline.hrv else 40.0
            delta_hrv = hrv - baseline_hrv
            delta_str = f"+{delta_hrv:.0f}ms" if delta_hrv > 0 else f"{delta_hrv:.0f}ms"
            status = "🟢" if hrv >= baseline_hrv else "🟡"
            lines.append(f"      {status} HRV: {hrv}ms ({delta_str})")
        if rhr:
            baseline_rhr = baseline.rhr.mean if baseline.rhr else 60.0
            delta_rhr = rhr - baseline_rhr
            delta_str = f"+{delta_rhr:.0f}bpm" if delta_rhr > 0 else f"{delta_rhr:.0f}bpm"
            status = "🟢" if rhr <= baseline_rhr else "🟡"
            lines.append(f"      {status} RHR: {rhr}bpm ({delta_str})")
    
    # Bedtime/ latency
    latency = sleep.get("latency")
    bedtime = sleep.get("bedtime_start")
    
    if latency:
        lat_min = int(latency / 60)
        lines.append(f"\n   ⏱️ Sleep latency: {lat_min} min")
    
    # Actionable suggestion
    lines.append(f"\n💡 *{suggestion}*")
    lines.append("\n_Good morning! Have a great day._ ☀️")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Daily Oura Health Report (Hybrid)")
    parser.add_argument("--date", help="Date (YYYY-MM-DD, default: today - the day you woke up)")
    parser.add_argument("--baseline-days", type=int, default=30, help="Days for baseline")
    args = parser.parse_args()
    
    try:
        report = generate_report(args.date, args.baseline_days)
        print(report)
    except Exception as e:
        error_msg = f"❌ Error generating report: {e}"
        print(error_msg)
        sys.exit(1)


if __name__ == "__main__":
    main()

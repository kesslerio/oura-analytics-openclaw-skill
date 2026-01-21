#!/usr/bin/env python3
"""
Oura Morning Briefing CLI

Generate concise, actionable daily briefings.

Usage:
    python oura_briefing.py                    # Today's briefing
    python oura_briefing.py --date 2026-01-20  # Specific date
    python oura_briefing.py --verbose          # Detailed briefing
    python oura_briefing.py --format json      # JSON output
    python oura_briefing.py --format brief     # 3-line brief
"""

import argparse
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

# Add scripts dir to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from oura_api import OuraClient
from schema import create_night_record
from briefing import BriefingFormatter, Baseline, format_brief_briefing, format_json_briefing


def main():
    parser = argparse.ArgumentParser(description="Oura Morning Briefing")
    parser.add_argument("--date", help="Date for briefing (YYYY-MM-DD, default: today)")
    parser.add_argument("--token", help="Oura API token")
    parser.add_argument("--verbose", action="store_true", help="Detailed briefing with driver analysis")
    parser.add_argument("--format", choices=["text", "brief", "json"], default="text",
                       help="Output format (text=full briefing, brief=3 lines, json=structured)")
    parser.add_argument("--baseline-days", type=int, default=14,
                       help="Days to use for baseline calculation (default: 14)")
    
    args = parser.parse_args()
    
    try:
        # Initialize client
        client = OuraClient(args.token)
        
        # Determine date
        if args.date:
            target_date = args.date
        else:
            target_date = datetime.now().strftime("%Y-%m-%d")
        
        # Get data for target date
        sleep_data = client.get_sleep(target_date, target_date)
        readiness_data = client.get_readiness(target_date, target_date)
        activity_data = client.get_activity(target_date, target_date)
        
        # Bounds check: ensure arrays are not empty before accessing
        if not sleep_data and not readiness_data:
            print(f"No data available for {target_date}", file=sys.stderr)
            sys.exit(1)
        
        # Create night record (safe access with bounds check)
        night = create_night_record(
            date=target_date,
            sleep=sleep_data[0] if (sleep_data and len(sleep_data) > 0) else None,
            readiness=readiness_data[0] if (readiness_data and len(readiness_data) > 0) else None,
            activity=activity_data[0] if (activity_data and len(activity_data) > 0) else None
        )
        
        # Calculate baseline from historical data
        baseline_start = (datetime.strptime(target_date, "%Y-%m-%d") - timedelta(days=args.baseline_days)).strftime("%Y-%m-%d")
        baseline_end = (datetime.strptime(target_date, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
        
        baseline_sleep = client.get_sleep(baseline_start, baseline_end)
        baseline_readiness = client.get_readiness(baseline_start, baseline_end)
        
        # Create baseline nights for calculation (align by date, not index)
        baseline_nights = []
        readiness_by_date = {r["day"]: r for r in baseline_readiness}
        
        for sleep_entry in baseline_sleep:
            date = sleep_entry["day"]
            readiness_entry = readiness_by_date.get(date)
            
            baseline_night = create_night_record(
                date=date,
                sleep=sleep_entry,
                readiness=readiness_entry
            )
            baseline_nights.append(baseline_night)
        
        baseline = Baseline.from_history(baseline_nights) if baseline_nights else None
        
        # Format output
        if args.format == "json":
            output = format_json_briefing(night, baseline)
            print(json.dumps(output, indent=2))
        elif args.format == "brief":
            output = format_brief_briefing(night, baseline)
            print(output)
        else:  # text
            formatter = BriefingFormatter(baseline)
            output = formatter.format(night, verbose=args.verbose)
            print(output)
    
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

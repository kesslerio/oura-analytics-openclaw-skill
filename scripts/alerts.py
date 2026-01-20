#!/usr/bin/env python3
"""
Oura Alerts - Readiness & Sleep Alerts

Sends Telegram notifications when metrics drop below thresholds.
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    import requests
except ImportError:
    print("Install requests: pip install requests")
    sys.exit(1)

from oura_api import OuraClient


def seconds_to_hours(seconds):
    return round(seconds / 3600, 1) if seconds else None


def check_thresholds(sleep_data, readiness_data, thresholds):
    """Check all days against thresholds.

    Args:
        sleep_data: List of sleep records from get_sleep()
        readiness_data: List of readiness records from get_readiness()
        thresholds: Dict with readiness, efficiency, sleep_hours thresholds
    """
    # Build readiness lookup by day
    readiness_by_day = {r.get("day"): r for r in readiness_data}

    alerts = []

    for day in sleep_data:
        date = day.get("day")

        # Get readiness from proper endpoint (not nested in sleep)
        readiness_record = readiness_by_day.get(date)
        readiness_score = readiness_record.get("score") if readiness_record else None

        efficiency = day.get("efficiency", 100)
        duration_sec = day.get("total_sleep_duration", 0)
        duration_hours = seconds_to_hours(duration_sec)

        day_alerts = []

        # Only alert if readiness data is available and below threshold
        if readiness_score is not None and readiness_score < thresholds.get("readiness", 60):
            day_alerts.append(f"Readiness {readiness_score}")
        # Note: Missing readiness data does not trigger alert (data may be pending)

        if efficiency < thresholds.get("efficiency", 80):
            day_alerts.append(f"Efficiency {efficiency}%")

        if duration_hours and duration_hours < thresholds.get("sleep_hours", 7):
            day_alerts.append(f"Sleep {duration_hours}h")

        if day_alerts:
            alerts.append({"date": date, "alerts": day_alerts})

    return alerts


def format_alert_message(alerts):
    """Format alerts for Telegram"""
    if not alerts:
        return None
    
    msg = "⚠️ *Oura Alerts*\n\n"
    
    for alert in alerts[-5:]:  # Last 5 alerts
        msg += f"📅 *{alert['date']}*\n"
        for a in alert["alerts"]:
            msg += f"   • {a}\n"
        msg += "\n"
    
    msg += f"_Total: {len(alerts)} alert days_"
    return msg


def send_telegram(message, chat_id=None, bot_token=None):
    """Send to Telegram"""
    chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")
    bot_token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN")
    
    if not chat_id or not bot_token:
        print("TELEGRAM_CHAT_ID or TELEGRAM_BOT_TOKEN not set")
        return False
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    resp = requests.post(url, json=data)
    return resp.status_code == 200


def main():
    parser = argparse.ArgumentParser(description="Oura Alerts")
    parser.add_argument("--days", type=int, default=7, help="Check period")
    parser.add_argument("--readiness", type=int, default=60, help="Readiness threshold")
    parser.add_argument("--efficiency", type=int, default=80, help="Efficiency threshold")
    parser.add_argument("--sleep-hours", type=float, default=7, help="Sleep hours threshold")
    parser.add_argument("--telegram", action="store_true", help="Send to Telegram")
    parser.add_argument("--token", help="Oura API token")
    
    args = parser.parse_args()
    
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d")
    
    try:
        client = OuraClient(args.token)
        sleep = client.get_sleep(start_date, end_date)
        readiness = client.get_readiness(start_date, end_date)

        thresholds = {
            "readiness": args.readiness,
            "efficiency": args.efficiency,
            "sleep_hours": args.sleep_hours
        }

        alerts = check_thresholds(sleep, readiness, thresholds)
        
        if alerts:
            print(f"\n⚠️  {len(alerts)} Alert Days Found:\n")
            for alert in alerts:
                print(f"  {alert['date']}: {', '.join(alert['alerts'])}")
            
            if args.telegram:
                msg = format_alert_message(alerts)
                if msg and send_telegram(msg):
                    print("\n✅ Alerts sent to Telegram!")
                else:
                    print("\n❌ Telegram failed")
        else:
            print(f"\n✅ All metrics above thresholds!")
            print(f"   Readiness > {args.readiness}")
            print(f"   Efficiency > {args.efficiency}%")
            print(f"   Sleep > {args.sleep_hours}h")
        
        # Save to file
        alert_file = f"/home/art/clawd-research/reports/oura_alerts_{end_date}.json"
        os.makedirs(os.path.dirname(alert_file), exist_ok=True)
        with open(alert_file, "w") as f:
            json.dump({"period": f"{start_date} to {end_date}", "alerts": alerts}, f, indent=2)
        print(f"\n💾 Saved to {alert_file}")
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

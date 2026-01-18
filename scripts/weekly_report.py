#!/usr/bin/env python3
import argparse
"""
Oura Weekly Report Generator

Generates automated weekly health reports and can send to Telegram.
"""

import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

try:
    import requests
except ImportError:
    print("Install requests: pip install requests")
    sys.exit(1)


class OuraClient:
    """Oura Cloud API client"""
    
    BASE_URL = "https://api.ouraring.com/v2/usercollection"
    
    def __init__(self, token=None):
        self.token = token or os.environ.get("OURA_API_TOKEN")
        if not self.token:
            raise ValueError("OURA_API_TOKEN not set")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def _request(self, endpoint, start_date=None, end_date=None):
        url = f"{self.BASE_URL}/{endpoint}"
        params = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        resp = requests.get(url, headers=self.headers, params=params)
        resp.raise_for_status()
        return resp.json().get("data", [])
    
    def get_sleep(self, start_date, end_date):
        return self._request("sleep", start_date, end_date)


def seconds_to_hours(seconds):
    return round(seconds / 3600, 1) if seconds else None


def calculate_sleep_score(day):
    efficiency = day.get("efficiency", 0)
    duration_hours = seconds_to_hours(day.get("total_sleep_duration", 0)) or 0
    eff_score = min(efficiency, 100)
    dur_score = min(duration_hours / 8 * 100, 100)
    return round((eff_score * 0.6) + (dur_score * 0.4), 1)


def analyze_week(sleep_data):
    """Analyze weekly data"""
    if not sleep_data:
        return None
    
    scores = [calculate_sleep_score(d) for d in sleep_data]
    efficiencies = [d.get("efficiency", 0) for d in sleep_data]
    durations = [seconds_to_hours(d.get("total_sleep_duration", 0)) for d in sleep_data]
    
    readiness_scores = []
    for d in sleep_data:
        r = d.get("readiness", {})
        if r and r.get("score"):
            readiness_scores.append(r["score"])
    
    return {
        "avg_sleep_score": round(sum(scores) / len(scores), 1) if scores else None,
        "avg_readiness": round(sum(readiness_scores) / len(readiness_scores), 1) if readiness_scores else None,
        "avg_efficiency": round(sum(efficiencies) / len(efficiencies), 1) if efficiencies else None,
        "avg_duration": round(sum(durations) / len(durations), 1) if durations else None,
        "best_day": max(sleep_data, key=lambda x: calculate_sleep_score(x)).get("day") if sleep_data else None,
        "worst_day": min(sleep_data, key=lambda x: calculate_sleep_score(x)).get("day") if sleep_data else None,
        "days_tracked": len(sleep_data)
    }


def format_telegram_message(week_data, period):
    """Format report for Telegram"""
    emoji = {
        "sleep": "😴",
        "readiness": "⚡",
        "efficiency": "📊",
        "duration": "⏰",
        "best": "🏆",
        "worst": "⚠️"
    }
    
    msg = f"📈 *Oura Weekly Report* ({period})\n\n"
    msg += f"{emoji['sleep']} Sleep Score: *{week_data['avg_sleep_score']}*/100\n"
    msg += f"{emoji['readiness']} Readiness: *{week_data['avg_readiness']}*/100\n"
    msg += f"{emoji['efficiency']} Efficiency: *{week_data['avg_efficiency']}%*\n"
    msg += f"{emoji['duration']} Avg Sleep: *{week_data['avg_duration']}h*\n"
    msg += f"\n{emoji['best']} Best Day: {week_data['best_day']}\n"
    msg += f"{emoji['worst']} Worst Day: {week_data['worst_day']}\n"
    msg += f"\n_Tracked: {week_data['days_tracked']} days_"
    
    return msg


def send_telegram(message, chat_id=None, bot_token=None):
    """Send report to Telegram"""
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
    parser = argparse.ArgumentParser(description="Oura Weekly Report")
    parser.add_argument("--days", type=int, default=7, help="Report period")
    parser.add_argument("--telegram", action="store_true", help="Send to Telegram")
    parser.add_argument("--token", help="Oura API token")
    
    args = parser.parse_args()
    
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d")
    period = f"{start_date} → {end_date}"
    
    try:
        client = OuraClient(args.token)
        sleep = client.get_sleep(start_date, end_date)
        week_data = analyze_week(sleep)
        
        if not week_data:
            print("No data available")
            sys.exit(1)
        
        # Print nicely
        print(f"\n📊 Oura Weekly Report ({period})")
        print(f"   Sleep Score: {week_data['avg_sleep_score']}")
        print(f"   Readiness: {week_data['avg_readiness']}")
        print(f"   Efficiency: {week_data['avg_efficiency']}%")
        print(f"   Avg Duration: {week_data['avg_duration']}h")
        print(f"   Best Day: {week_data['best_day']}")
        print(f"   Worst Day: {week_data['worst_day']}")
        print(f"   Days Tracked: {week_data['days_tracked']}")
        
        # Send to Telegram
        if args.telegram:
            msg = format_telegram_message(week_data, period)
            if send_telegram(msg):
                print("\n✅ Sent to Telegram!")
            else:
                print("\n❌ Telegram failed")
        
        # Save to file
        report_file = f"/home/art/clawd-research/reports/oura_weekly_{end_date}.json"
        os.makedirs(os.path.dirname(report_file), exist_ok=True)
        with open(report_file, "w") as f:
            json.dump({"period": period, "summary": week_data, "raw": sleep}, f, indent=2)
        print(f"\n💾 Saved to {report_file}")
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Oura Cloud API Wrapper

Usage:
    python oura_api.py sleep --days 7
    python oura_api.py readiness --days 7
    python oura_api.py report --type weekly
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path

try:
    import requests
except ImportError:
    print("Install requests: pip install requests")
    sys.exit(1)

SKILL_DIR = Path(__file__).parent.parent

class OuraClient:
    """Oura Cloud API client"""
    
    BASE_URL = "https://api.ouraring.com/v2/usercollection"
    
    def __init__(self, token=None):
        self.token = token or os.environ.get("OURA_API_TOKEN")
        if not self.token:
            raise ValueError("OURA_API_TOKEN not set. Get it at https://cloud.ouraring.com/personal-access-token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def _request(self, endpoint, start_date=None, end_date=None):
        """Make API request"""
        url = f"{self.BASE_URL}/{endpoint}"
        params = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        
        resp = requests.get(url, headers=self.headers, params=params)
        resp.raise_for_status()
        return resp.json().get("data", [])
    
    def get_sleep(self, start_date=None, end_date=None):
        """Fetch sleep data (summary)"""
        return self._request("sleep", start_date, end_date)
    
    def get_daily_sleep(self, start_date=None, end_date=None):
        """Fetch detailed sleep data"""
        return self._request("daily_sleep", start_date, end_date)
    
    def get_readiness(self, start_date=None, end_date=None):
        """Fetch readiness data"""
        return self._request("daily_readiness", start_date, end_date)
    
    def get_activity(self, start_date=None, end_date=None):
        """Fetch activity data"""
        return self._request("daily_activity", start_date, end_date)
    
    def get_hrv(self, start_date=None, end_date=None):
        """Fetch HRV data"""
        return self._request("hrv", start_date, end_date)

    def get_recent_sleep(self, days=2):
        """Fetch and merge recent sleep data (daily + detailed).

        Oura data is processed with delay - get last few days and merge
        daily_sleep scores with detailed sleep data.
        """
        # Oura data is processed with delay - get last few days
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")

        # Get daily sleep scores
        resp_daily = requests.get(
            f"{self.BASE_URL}/daily_sleep",
            headers=self.headers,
            params={"start_date": start_date, "end_date": end_date}
        )
        resp_daily.raise_for_status()
        daily_data = {item["day"]: item for item in resp_daily.json().get("data", [])}

        # Get detailed sleep data
        resp_sleep = requests.get(
            f"{self.BASE_URL}/sleep",
            headers=self.headers,
            params={"start_date": start_date, "end_date": end_date}
        )
        resp_sleep.raise_for_status()
        sleep_data = resp_sleep.json().get("data", [])

        # Merge: add scores to sleep data
        for item in sleep_data:
            day = item.get("day")
            if day in daily_data:
                item["score"] = daily_data[day].get("score")

        # Return last N entries
        return sleep_data[-days:] if len(sleep_data) >= days else sleep_data

    def get_weekly_summary(self):
        """Fetch weekly sleep summary"""
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        return self.get_sleep(start_date, end_date)


class OuraAnalyzer:
    """Analyze Oura data"""
    
    def __init__(self, sleep_data=None, readiness_data=None, activity_data=None):
        self.sleep = sleep_data or []
        self.readiness = readiness_data or []
        self.activity = activity_data or []
    
    @staticmethod
    def seconds_to_hours(seconds):
        """Convert seconds to hours"""
        return round(seconds / 3600, 1) if seconds else None
    
    @staticmethod
    def calculate_sleep_score(day):
        """Calculate approximate sleep score from available metrics"""
        efficiency = day.get("efficiency", 0)
        duration_sec = day.get("total_sleep_duration", 0)
        duration_hours = duration_sec / 3600 if duration_sec else 0
        
        # Oura's algorithm approximation:
        eff_score = min(efficiency, 100)
        dur_score = min(duration_hours / 8 * 100, 100)  # 8 hours = 100%
        
        return round((eff_score * 0.6) + (dur_score * 0.4), 1)
    
    def average_metric(self, data, metric, convert_to_hours=False):
        """Calculate average of a metric"""
        if not data:
            return None
        values = []
        for d in data:
            val = d.get(metric)
            if val is not None:
                if convert_to_hours:
                    val = self.seconds_to_hours(val)
                values.append(val)
        return round(sum(values) / len(values), 2) if values else None
    
    def trend(self, data, metric, days=7):
        """Calculate trend over N days"""
        if len(data) < 2:
            return 0
        recent = data[-days:]
        if len(recent) < 2:
            return 0
        first = recent[0].get(metric, 0)
        last = recent[-1].get(metric, 0)
        return round(last - first, 2)
    
    def summary(self):
        """Generate summary"""
        avg_sleep_hours = self.average_metric(self.sleep, "total_sleep_duration", convert_to_hours=True)
        avg_efficiency = self.average_metric(self.sleep, "efficiency")
        avg_hrv = self.average_metric(self.sleep, "average_hrv")
        
        # Calculate average sleep score
        sleep_scores = [self.calculate_sleep_score(d) for d in self.sleep]
        avg_sleep_score = round(sum(sleep_scores) / len(sleep_scores), 1) if sleep_scores else None
        
        # Readiness from nested object in sleep data
        readiness_scores = []
        for day in self.sleep:
            readiness = day.get("readiness", {})
            if readiness and readiness.get("score"):
                readiness_scores.append(readiness["score"])
        avg_readiness = round(sum(readiness_scores) / len(readiness_scores), 1) if readiness_scores else None
        
        return {
            "avg_sleep_score": avg_sleep_score,
            "avg_readiness_score": avg_readiness,
            "avg_sleep_hours": avg_sleep_hours,
            "avg_sleep_efficiency": avg_efficiency,
            "avg_hrv": avg_hrv,
            "days_tracked": len(self.sleep)
        }


class OuraReporter:
    """Generate Oura reports"""
    
    def __init__(self, client):
        self.client = client
    
    def generate_report(self, report_type="weekly", days=None):
        """Generate report"""
        if not days:
            days = 7 if report_type == "weekly" else 30
        
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        sleep = self.client.get_sleep(start_date, end_date)
        readiness = self.client.get_readiness(start_date, end_date)
        activity = self.client.get_activity(start_date, end_date)
        
        analyzer = OuraAnalyzer(sleep, readiness, activity)
        summary = analyzer.summary()
        
        return {
            "report_type": report_type,
            "period": f"{start_date} to {end_date}",
            "summary": summary,
            "daily_data": {
                "sleep": sleep,
                "readiness": readiness,
                "activity": activity
            }
        }


def main():
    parser = argparse.ArgumentParser(description="Oura Analytics CLI")
    parser.add_argument("command", choices=["sleep", "daily_sleep", "readiness", "activity", "report", "summary", "comparison"],
                       help="Data type to fetch or report type")
    parser.add_argument("--days", type=int, default=7, help="Number of days")
    parser.add_argument("--type", default="weekly", help="Report type")
    parser.add_argument("--token", help="Oura API token")
    
    args = parser.parse_args()
    
    try:
        client = OuraClient(args.token)
        
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d")
        
        if args.command == "sleep":
            data = client.get_sleep(start_date, end_date)
            print(json.dumps(data, indent=2))
            
        elif args.command == "daily_sleep":
            data = client.get_daily_sleep(start_date, end_date)
            print(json.dumps(data, indent=2))
        
        elif args.command == "readiness":
            data = client.get_readiness(start_date, end_date)
            print(json.dumps(data, indent=2))
        
        elif args.command == "activity":
            data = client.get_activity(start_date, end_date)
            print(json.dumps(data, indent=2))
        
        elif args.command == "summary":
            sleep = client.get_sleep(start_date, end_date)
            # readiness = client.get_readiness(start_date, end_date) # Unused in analyzer currently if passing only sleep
            analyzer = OuraAnalyzer(sleep)
            summary = analyzer.summary()
            print(json.dumps(summary, indent=2))

        elif args.command == "comparison":
            # Fetch 2x days
            doubled_days = args.days * 2
            start_date_extended = (datetime.now() - timedelta(days=doubled_days)).strftime("%Y-%m-%d")
            
            sleep = client.get_sleep(start_date_extended, end_date)
            
            # Sort by date
            sleep = sorted(sleep, key=lambda x: x.get('day'))
            
            # Split into Current (last N days) and Previous (N days before that)
            current_sleep = sleep[-args.days:] if len(sleep) > 0 else []
            previous_sleep = sleep[:-args.days][-args.days:] if len(sleep) > args.days else []
            
            analyzer_curr = OuraAnalyzer(current_sleep)
            analyzer_prev = OuraAnalyzer(previous_sleep)
            
            summary_curr = analyzer_curr.summary()
            summary_prev = analyzer_prev.summary()
            
            diff = {}
            for key in summary_curr:
                curr_val = summary_curr.get(key)
                prev_val = summary_prev.get(key)
                if isinstance(curr_val, (int, float)) and isinstance(prev_val, (int, float)):
                    diff[key] = round(curr_val - prev_val, 2)
                else:
                    diff[key] = None
            
            print(json.dumps({
                "current": summary_curr,
                "previous": summary_prev,
                "diff": diff
            }, indent=2))
        
        elif args.command == "report":
            reporter = OuraReporter(client)
            report = reporter.generate_report(args.type, args.days)
            print(json.dumps(report, indent=2))
    
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("Set OURA_API_TOKEN environment variable or use --token", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"API Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

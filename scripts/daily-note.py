#!/usr/bin/env python3
"""
Daily Note Generator for Obsidian
Runs via OpenClaw cron at 8:15am Pacific
Creates /home/art/Obsidian/01-TODOs/Daily/YYYY-MM-DD.md with Oura data

Requirements:
    - OURA_API_TOKEN environment variable must be set
    - oura_api.py must be in the same directory (scripts/)

Usage:
    python daily-note.py
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add this script's directory to path for oura_api import
sys.path.insert(0, str(Path(__file__).parent))

from oura_api import OuraClient

OBSIDIAN_DAILY = Path("/home/art/Obsidian/01-TODOs/Daily")
OURA_TOKEN = os.environ.get("OURA_API_TOKEN")


def get_oura_data():
    """Fetch yesterday's sleep data (since we just woke up) and today's readiness."""
    if not OURA_TOKEN:
        print("Warning: OURA_API_TOKEN not set", file=sys.stderr)
        return {"sleep_score": "N/A", "readiness": "N/A", "hours": "N/A"}
    
    try:
        client = OuraClient(OURA_TOKEN)
        
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Get sleep data for last 3 days to ensure we have yesterday's
        sleep_records = client.get_recent_sleep(days=3)
        
        # Find sleep record for yesterday (by date, not by position)
        sleep_score = "N/A"
        hours = "N/A"
        if sleep_records:
            for record in sleep_records:
                record_date = record.get("day") or record.get("date", "")
                if record_date == yesterday:
                    duration_sec = record.get("total_sleep_duration", 0)
                    hours = round(duration_sec / 3600, 1) if duration_sec else "N/A"
                    
                    # Calculate sleep score from efficiency + duration
                    efficiency = record.get("efficiency", 0)
                    if efficiency and duration_sec:
                        eff_score = min(efficiency, 100)
                        dur_score = min((duration_sec / 3600) / 8 * 100, 100)
                        sleep_score = round((eff_score * 0.6) + (dur_score * 0.4))
                    else:
                        sleep_score = record.get("score", "N/A")
                    break
        
        # Get readiness for today (by date, not by position)
        readiness = "N/A"
        readiness_records = client.get_readiness(yesterday, today)
        if readiness_records:
            for record in readiness_records:
                record_date = record.get("day") or record.get("date", "")
                if record_date == today:
                    readiness = record.get("score", "N/A")
                    break
            # Fall back to most recent if today not found
            if readiness == "N/A" and readiness_records:
                readiness = readiness_records[-1].get("score", "N/A")
        
        return {
            "sleep_score": sleep_score,
            "readiness": readiness,
            "hours": hours
        }
    except Exception as e:
        print(f"Oura API error: {e}", file=sys.stderr)
        return {"sleep_score": "N/A", "readiness": "N/A", "hours": "N/A"}


def create_daily_note():
    """Create today's daily note in Obsidian."""
    today = datetime.now()
    date_str = today.strftime("%Y-%m-%d")
    date_display = today.strftime("%A, %B %d, %Y")
    yesterday_str = (today - timedelta(days=1)).strftime("%Y-%m-%d")
    tomorrow_str = (today + timedelta(days=1)).strftime("%Y-%m-%d")
    
    note_path = OBSIDIAN_DAILY / f"{date_str}.md"
    
    # Don't overwrite if exists
    if note_path.exists():
        print(f"Note already exists: {note_path}")
        return
    
    # Get Oura data
    oura = get_oura_data()
    
    # Create note content
    content = f"""# {date_display}

## 🌅 Morning Check-in

| Metric | Score |
|--------|-------|
| 😴 Sleep | {oura['sleep_score']}/100 |
| ⚡ Readiness | {oura['readiness']}/100 |
| ⏰ Hours Slept | {oura['hours']}h |

## 📋 Today's Priorities
- [ ] 
- [ ] 
- [ ] 

## 📝 Notes


## 🌙 Evening Reflection
*How did the day go?*


---
← [[{yesterday_str}]] | [[{tomorrow_str}]] →
"""
    
    # Ensure directory exists
    OBSIDIAN_DAILY.mkdir(parents=True, exist_ok=True)
    
    # Write note
    note_path.write_text(content)
    print(f"Created: {note_path}")


if __name__ == "__main__":
    create_daily_note()

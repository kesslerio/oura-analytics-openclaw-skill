#!/usr/bin/env python3
"""
Daily Note Generator for Obsidian
Runs via OpenClaw cron at 8:15am Pacific
Creates /home/art/Obsidian/01-Daily/YYYY-MM-DD.md with Oura data
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add oura-analytics to path
sys.path.insert(0, "/home/art/clawd/skills/oura-analytics/scripts")

from oura_api import OuraClient

OBSIDIAN_DAILY = Path("/home/art/Obsidian/01-Daily")
OURA_TOKEN = os.environ.get("OURA_API_TOKEN")


def get_oura_data():
    """Fetch today's Oura data (actually yesterday's sleep since we just woke up)"""
    if not OURA_TOKEN:
        return {"sleep_score": "N/A", "readiness": "N/A", "hours": "N/A"}
    
    try:
        client = OuraClient(OURA_TOKEN)
        
        # Get last night's sleep (yesterday's date in Oura)
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Get sleep data
        sleep = client.get_recent_sleep(days=2)
        if sleep:
            latest = sleep[-1] if sleep else {}
            duration_sec = latest.get("total_sleep_duration", 0)
            hours = round(duration_sec / 3600, 1) if duration_sec else "N/A"
            
            # Calculate sleep score from efficiency + duration
            efficiency = latest.get("efficiency", 0)
            if efficiency and duration_sec:
                eff_score = min(efficiency, 100)
                dur_score = min((duration_sec / 3600) / 8 * 100, 100)
                sleep_score = round((eff_score * 0.6) + (dur_score * 0.4))
            else:
                sleep_score = latest.get("score", "N/A")
        else:
            sleep_score = "N/A"
            hours = "N/A"
        
        # Get readiness
        readiness_data = client.get_readiness(yesterday, today)
        if readiness_data:
            readiness = readiness_data[-1].get("score", "N/A")
        else:
            readiness = "N/A"
        
        return {
            "sleep_score": sleep_score,
            "readiness": readiness,
            "hours": hours
        }
    except Exception as e:
        print(f"Oura API error: {e}", file=sys.stderr)
        return {"sleep_score": "N/A", "readiness": "N/A", "hours": "N/A"}


def create_daily_note():
    """Create today's daily note"""
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

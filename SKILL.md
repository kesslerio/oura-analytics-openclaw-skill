---
name: oura-analytics
description: Oura Ring data integration and analytics. Fetch sleep scores, readiness, activity, HRV, and trends from the Oura Cloud API. Generate automated reports, correlations with productivity, and trigger-based alerts for low recovery days.
metadata: {"clawdbot":{"requires":{"bins":["python3"],"env":["OURA_API_TOKEN"]},"homepage":"https://cloud.ouraring.com"}}
---

# Oura Analytics

## Quick Start

```bash
# Set Oura API token
export OURA_API_TOKEN="your_personal_access_token"

# Fetch sleep data (last 7 days)
python {baseDir}/scripts/oura_api.py sleep --days 7

# Get readiness summary
python {baseDir}/scripts/oura_api.py readiness --days 7

# Generate weekly report
python {baseDir}/scripts/oura_api.py report --type weekly
```

## When to Use

Use this skill when:
- Fetching Oura Ring metrics (sleep, readiness, activity, HRV)
- Analyzing recovery trends over time
- Correlating sleep quality with productivity/events
- Setting up automated alerts for low readiness
- Generating daily/weekly/monthly health reports

## Core Workflows

### 1. Data Fetching
```python
from oura_api import OuraClient

client = OuraClient(token=oura_api_token)
sleep_data = client.get_sleep(start_date="2026-01-01", end_date="2026-01-16")
readiness_data = client.get_readiness(start_date="2026-01-01", end_date="2026-01-16")
```

### 2. Trend Analysis
```python
from oura_api import OuraAnalyzer

analyzer = OuraAnalyzer(sleep_data, readiness_data)
avg_sleep = analyzer.average_metric("sleep_score")
avg_readiness = analyzer.average_metric("readiness_score")
trend = analyzer.trend("hrv_balance")
```

### 3. Alerts
```python
from alerts import OuraAlerts

alerts = OuraAlerts(thresholds={"readiness": 60, "sleep_score": 70})
low_days = alerts.find_low_days(readiness_data)
```

## Scripts

- `scripts/oura_api.py` - Oura Cloud API wrapper with OuraAnalyzer and OuraReporter classes
- `scripts/alerts.py` - Threshold-based notifications (CLI: `python {baseDir}/scripts/alerts.py --days 7 --readiness 60`)
- `scripts/weekly_report.py` - Weekly report generator

## References

- `references/api.md` - Oura Cloud API documentation
- `references/metrics.md` - Metric definitions and interpretations

## Automation (Cron Jobs)

Cron jobs are configured in Clawdbot's gateway, not in this repo. Add these to your Clawdbot setup:

### Daily Morning Briefing (8:00 AM)
```bash
clawdbot cron add \
  --name "Daily Oura Health Report (Hybrid)" \
  --cron "0 8 * * *" \
  --tz "America/Los_Angeles" \
  --session isolated \
  --wake next-heartbeat \
  --deliver \
  --channel telegram \
  --target "<YOUR_TELEGRAM_CHAT_ID>" \
  --message "Run the daily Oura health report with hybrid format: Execute bash /path/to/your/scripts/daily-oura-report-hybrid.sh"
```

### Weekly Sleep Report (Sunday 8:00 AM)
```bash
clawdbot cron add \
  --name "Weekly Oura Sleep Report" \
  --cron "0 8 * * 0" \
  --tz "America/Los_Angeles" \
  --session isolated \
  --wake next-heartbeat \
  --deliver \
  --channel telegram \
  --target "<YOUR_TELEGRAM_CHAT_ID>" \
  --message "Run weekly Oura sleep report: bash /path/to/your/oura-weekly-sleep-alert.sh"
```

### Daily Obsidian Note (8:15 AM)
```bash
clawdbot cron add \
  --name "Daily Obsidian Note" \
  --cron "15 8 * * *" \
  --tz "America/Los_Angeles" \
  --session isolated \
  --wake next-heartbeat \
  --message "Create daily Obsidian note with Oura data. Run: source /path/to/venv/bin/activate && python /path/to/daily-note.py"
```

**Note:** Replace `/path/to/your/` with your actual paths and `<YOUR_TELEGRAM_CHAT_ID>` with your Telegram channel/group ID.

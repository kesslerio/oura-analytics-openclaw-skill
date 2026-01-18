---
name: oura-analytics
description: Oura Ring data integration and analytics. Fetch sleep scores, readiness, activity, HRV, and trends from the Oura Cloud API. Generate automated reports, correlations with productivity, and trigger-based alerts for low recovery days.
---

# Oura Analytics

## Quick Start

```bash
# Set Oura API token
export OURA_API_TOKEN="your_personal_access_token"

# Fetch sleep data (last 7 days)
python /home/art/.clawdbot/skills/oura-analytics/scripts/oura_api.py sleep --days 7

# Get readiness summary
python /home/art/.clawdbot/skills/oura-analytics/scripts/oura_api.py readiness --days 7

# Generate weekly report
python /home/art/.clawdbot/skills/oura-analytics/scripts/oura_api.py report --type weekly
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
from analyzer import OuraAnalyzer

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

- `scripts/oura_api.py` - Oura Cloud API wrapper
- `scripts/analyzer.py` - Trend analysis and correlations
- `scripts/alerts.py` - Threshold-based notifications
- `scripts/report.py` - Report generation

## References

- `references/api.md` - Oura Cloud API documentation
- `references/metrics.md` - Metric definitions and interpretations

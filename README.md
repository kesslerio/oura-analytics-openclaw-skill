# Oura Analytics - Clawdbot Skill

[![Clawdbot Official](https://img.shields.io/badge/clawdbot-official%20skill-blue)](https://github.com/cktang88/clawdbot)
[![ClawdHub](https://img.shields.io/badge/clawdhub-production-green)](https://clawdhub.com)

**Production-grade Oura Ring data integration for Clawdbot**  
Fetch sleep scores, readiness, activity, HRV, and trends from Oura Cloud API. Generate automated health reports and trigger-based alerts.

## Features

✅ **Oura Cloud API Integration** - Personal Access Token authentication  
✅ **Sleep Analytics** - Score, duration, efficiency, REM/deep stages  
✅ **Readiness Tracking** - Recovery score, HRV balance, temperature  
✅ **Activity Metrics** - Steps, calories, MET minutes  
✅ **Trend Analysis** - Moving averages, correlations, anomaly detection  
✅ **Automated Alerts** - Low readiness/sleep notifications via Telegram

## Why This Exists

Clawdbot needs access to Oura Ring health data for:
- Daily morning briefings ("How did I sleep?")
- Correlating recovery with productivity/calendar
- Automated alerts for low recovery days
- Weekly/monthly health trend reports

**This skill provides:**
- Simple Python API client for Oura Cloud API v2
- Trend analysis and correlation tools
- Threshold-based alerting system
- Report generation templates

## Installation

### 1. Get Oura Personal Access Token

1. Go to https://cloud.ouraring.com/personal-access-tokens
2. Create new token (select all scopes)
3. Copy token to secrets file:

```bash
echo 'OURA_API_TOKEN="your_token_here"' >> ~/.config/systemd/user/secrets.conf
```

### 2. Install the skill

```bash
git clone https://github.com/kesslerio/oura-analytics-clawdbot-skill.git ~/.clawdbot/skills/oura-analytics
pip install requests python-telegram-bot
```

### 3. Add to Clawdbot's TOOLS.md

```markdown
### oura-analytics
- Fetch Oura Ring metrics (sleep, readiness, activity, HRV)
- Generate health reports and correlations
- Set up automated alerts for low recovery
- Usage: `python ~/.clawdbot/skills/oura-analytics/scripts/oura_api.py sleep --days 7`
```

## Usage Examples

### Fetch Sleep Data

```bash
# Last 7 days
python scripts/oura_api.py sleep --days 7
```

### Get Readiness Summary

```bash
python scripts/oura_api.py readiness --days 7
```

### Generate Reports

```bash
# Weekly summary (last 7 days)
python scripts/weekly_report.py --days 7

# Monthly trends (last 30 days)
python scripts/weekly_report.py --days 30
```

### Trigger Alerts

```bash
# Check for low readiness and send Telegram notification
python scripts/alerts.py --days 7 --readiness 60 --efficiency 80 --telegram
```

## Core Workflows

### 1. Morning Health Check

```python
from oura_api import OuraClient, OuraAnalyzer

client = OuraClient(token=os.getenv("OURA_API_TOKEN"))
sleep_data = client.get_sleep(start_date="2026-01-18", end_date="2026-01-18")
today = sleep_data[0] if sleep_data else {}

if today:
    print(f"Sleep Score: {today.get('score', 'N/A')}/100")
    print(f"Total Sleep: {today.get('total_sleep_duration', 0)/3600:.1f}h")
    print(f"REM: {today.get('rem_sleep_duration', 0)/3600:.1f}h")
    print(f"Deep: {today.get('deep_sleep_duration', 0)/3600:.1f}h")
```

### 2. Recovery Tracking

```python
readiness = client.get_readiness(start_date="2026-01-11", end_date="2026-01-18")
avg_readiness = sum(d.get('score', 0) for d in readiness) / len(readiness) if readiness else 0
print(f"7-day avg readiness: {avg_readiness:.0f}")
```

### 3. Trend Analysis

```python
from oura_api import OuraAnalyzer

analyzer = OuraAnalyzer(sleep_data, readiness_data)
avg_sleep = analyzer.average_metric(sleep_data, "score")
avg_readiness = analyzer.average_metric(readiness_data, "score")
print(f"Avg Sleep Score: {avg_sleep}")
print(f"Avg Readiness Score: {avg_readiness}")
```

## API Client Reference

### OuraClient

```python
client = OuraClient(token="your_token")

# Sleep data (date range required)
sleep = client.get_sleep(start_date="2026-01-01", end_date="2026-01-16")

# Readiness data
readiness = client.get_readiness(start_date="2026-01-01", end_date="2026-01-16")

# Activity data
activity = client.get_activity(start_date="2026-01-01", end_date="2026-01-16")

# HRV trends
hrv = client.get_hrv(start_date="2026-01-01", end_date="2026-01-16")
```

### OuraAnalyzer

```python
from oura_api import OuraClient, OuraAnalyzer

client = OuraClient(token="your_token")
sleep = client.get_sleep(start_date="2026-01-01", end_date="2026-01-16")
readiness = client.get_readiness(start_date="2026-01-01", end_date="2026-01-16")

analyzer = OuraAnalyzer(sleep_data=sleep, readiness_data=readiness)

# Average metrics
avg_sleep = analyzer.average_metric(sleep, "score")
avg_readiness = analyzer.average_metric(readiness, "score")

# Trend analysis
trend = analyzer.trend(sleep, "score", days=7)

# Summary
summary = analyzer.summary()
```

### OuraReporter

```python
from oura_api import OuraClient, OuraReporter

client = OuraClient(token="your_token")
reporter = OuraReporter(client)

# Generate weekly report
report = reporter.generate_report(report_type="weekly", days=7)
print(json.dumps(report, indent=2))
```

## Telegram Bot Integration

Optional: Run as standalone Telegram bot for daily notifications.

```bash
# Set bot token
echo 'TELEGRAM_BOT_TOKEN="your_bot_token"' >> ~/.config/systemd/user/secrets.conf
echo 'TELEGRAM_CHAT_ID="your_chat_id"' >> ~/.config/systemd/user/secrets.conf

# Run bot
python scripts/telegram_bot.py
```

## Metrics Reference

| Metric | Description | Range |
|--------|-------------|-------|
| **Sleep Score** | Overall sleep quality | 0-100 |
| **Readiness Score** | Recovery readiness | 0-100 |
| **HRV Balance** | Heart rate variability | -3 to +3 |
| **Sleep Efficiency** | Time asleep / time in bed | 0-100% |
| **REM Sleep** | REM stage duration | hours |
| **Deep Sleep** | Deep stage duration | hours |
| **Temperature Deviation** | Body temp vs baseline | °C |

See `references/metrics.md` for full definitions.

## Architecture

- **`scripts/oura_api.py`** - Oura Cloud API v2 client with OuraAnalyzer and OuraReporter classes
- **`scripts/alerts.py`** - Threshold-based alerting CLI
- **`scripts/weekly_report.py`** - Weekly report generator
- **`scripts/telegram_bot.py`** - Optional Telegram bot integration
- **`references/`** - API docs, metric definitions

## Troubleshooting

### Authentication Failed

```bash
# Check token is set
echo $OURA_API_TOKEN

# Or use explicit token
python scripts/oura_api.py sleep --days 7 --token "your_token"
```

### No Data Returned

```bash
# Check date range (Oura data has ~24h delay)
python scripts/oura_api.py sleep --days 10

# Or fetch and inspect manually
python scripts/oura_api.py sleep --days 7 | python -m json.tool | head -50
```

## Credits

**Created for production Clawdbot health tracking**  
Developed by [@kesslerio](https://github.com/kesslerio) • Part of the [ClawdHub](https://clawdhub.com) ecosystem

**Powered by:**
- [Oura Ring](https://ouraring.com/) - Wearable health tracker
- [Oura Cloud API v2](https://cloud.ouraring.com/v2/docs) - Official API

## License

MIT

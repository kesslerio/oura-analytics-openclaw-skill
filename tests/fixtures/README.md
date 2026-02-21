# Test fixtures for Oura Analytics skill

## sleep_response.json
Mock sleep data from Oura Cloud API
```json
[
  {
    "day": "2026-01-15",
    "score": 82,
    "efficiency": 89,
    "total_sleep_duration": 25200,
    "rem_sleep_duration": 7200,
    "deep_sleep_duration": 5400,
    "average_hrv": 45
  },
  {
    "day": "2026-01-16",
    "score": 78,
    "efficiency": 85,
    "total_sleep_duration": 23400,
    "rem_sleep_duration": 6480,
    "deep_sleep_duration": 4680,
    "average_hrv": 42
  }
]
```

## readiness_response.json
Mock readiness data from Oura Cloud API
```json
[
  {
    "day": "2026-01-15",
    "score": 75,
    "contributors": {
      "sleep_balance": 75,
      "recovery_index": 80
    }
  },
  {
    "day": "2026-01-16",
    "score": 68,
    "contributors": {
      "sleep_balance": 65,
      "recovery_index": 70
    }
  }
]
```

## sample_events.jsonl
Sample calendar events for correlation
```jsonl
{"date": "2026-01-15", "name": "Meeting with team", "category": "work"}
{"date": "2026-01-16", "name": "Late dinner", "category": "lifestyle"}
```

## stress_direct_response.json
Mock direct daily stress records
```json
[
  {"day": "2026-01-15", "stress_score": 62, "day_summary": "stressed"},
  {"day": "2026-01-16", "stress_score": 38, "day_summary": "restored"}
]
```

## stress_proxy_inputs.json
Mock sleep/readiness records for stress proxy derivation tests
```json
{
  "sleep": [{"day": "2026-01-15", "average_hrv": 30, "lowest_heart_rate": 64}],
  "readiness": [{"day": "2026-01-15", "contributors": {"hrv_balance": 60}}]
}
```

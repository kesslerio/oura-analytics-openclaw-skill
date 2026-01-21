#!/usr/bin/env python3
"""
Timezone Utilities for Oura Analytics

Handles timezone-aware day alignment, travel detection, and DST handling.
"""

import os
import pytz
from datetime import datetime, date
from typing import Optional, Tuple


def get_user_timezone() -> str:
    """Get user's configured timezone or default to America/Los_Angeles."""
    return os.environ.get("USER_TIMEZONE", "America/Los_Angeles")


def get_canonical_day(utc_timestamp: str, user_tz: Optional[str] = None) -> Tuple[date, str]:
    """
    Convert a UTC timestamp to the user's canonical day.

    Args:
        utc_timestamp: ISO format timestamp (e.g., "2026-01-15T00:00:00.000+00:00")
        user_tz: User's timezone (default: from USER_TIMEZONE env or America/Los_Angeles)

    Returns:
        Tuple of (date object, timezone-aware datetime)
    """
    if user_tz is None:
        user_tz = get_user_timezone()

    try:
        # Parse the UTC timestamp
        # Handle both +00:00 and Z format
        ts_clean = utc_timestamp.replace("Z", "+00:00")
        utc_dt = datetime.fromisoformat(ts_clean)

        # Convert to user's timezone
        user_tz_obj = pytz.timezone(user_tz)
        local_dt = utc_dt.astimezone(user_tz_obj)

        return local_dt.date(), local_dt
    except (ValueError, pytz.UnknownTimeZoneError) as e:
        # Fallback: return the date from the timestamp as-is
        fallback_date = datetime.fromisoformat(utc_timestamp[:10]).date()
        return fallback_date, None


def get_canonical_day_from_date_str(date_str: str, user_tz: Optional[str] = None) -> date:
    """
    Get canonical day from a date string (YYYY-MM-DD).

    For dates, we assume the date is in the user's local timezone.
    """
    if user_tz is None:
        user_tz = get_user_timezone()

    try:
        # Parse the date as midnight in user's timezone
        user_tz_obj = pytz.timezone(user_tz)
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        local_dt = user_tz_obj.localize(dt)
        return local_dt.date()
    except (ValueError, pytz.UnknownTimeZoneError):
        # Fallback: return parsed date directly
        return datetime.strptime(date_str, "%Y-%m-%d").date()


def is_travel_day(sleep_records: list, threshold_hours: float = 3.0) -> list:
    """
    Detect potential travel days based on bedtime shifts.

    Args:
        sleep_records: List of sleep records with bedtime_start
        threshold_hours: Minimum hour shift to flag as potential travel

    Returns:
        List of dates that may be travel days
    """
    if not sleep_records or len(sleep_records) < 2:
        return []

    travel_days = []
    user_tz = get_user_timezone()

    # Extract bedtimes in user's local hour
    bedtimes = []
    for record in sleep_records:
        canonical_day, local_dt = get_canonical_day(record.get("bedtime_start", ""), user_tz)
        if local_dt:
            bedtimes.append((canonical_day, local_dt.hour + local_dt.minute / 60))

    # Find large shifts (> threshold_hours from median)
    if len(bedtimes) < 3:
        return []

    hours = [h for _, h in bedtimes]
    median_hour = sorted(hours)[len(hours) // 2]

    for day, hour in bedtimes:
        shift = abs(hour - median_hour)
        if shift > threshold_hours or (24 - shift) > threshold_hours:
            if day not in travel_days:
                travel_days.append(day)

    return travel_days


def get_sleep_for_canonical_day(sleep_data: list, target_date: date,
                                  user_tz: Optional[str] = None) -> list:
    """
    Get all sleep records that belong to a canonical day.

    Oura assigns sleep to the wake date, but sleep starting the previous
    day may still be relevant for the "night before".
    """
    if user_tz is None:
        user_tz = get_user_timezone()

    matching = []
    for record in sleep_data:
        record_day_str = record.get("day")
        if not record_day_str:
            continue

        canonical_day = get_canonical_day_from_date_str(record_day_str, user_tz)

        if canonical_day == target_date:
            matching.append(record)

    return matching


def group_by_canonical_day(data: list, timestamp_field: str = "day",
                           user_tz: Optional[str] = None) -> dict:
    """
    Group data records by canonical day.

    Args:
        data: List of records with a date field
        timestamp_field: Field name containing the date (e.g., "day" or "bedtime_start")
        user_tz: User's timezone

    Returns:
        Dict mapping date strings to lists of records
    """
    if user_tz is None:
        user_tz = get_user_timezone()

    grouped = {}
    for record in data:
        if timestamp_field == "day":
            canonical = get_canonical_day_from_date_str(record.get("day", ""), user_tz)
        else:
            canonical, _ = get_canonical_day(record.get(timestamp_field, ""), user_tz)

        date_str = canonical.isoformat()
        if date_str not in grouped:
            grouped[date_str] = []
        grouped[date_str].append(record)

    return grouped


def format_localized_datetime(utc_timestamp: str, fmt: str = "%Y-%m-%d %H:%M",
                               user_tz: Optional[str] = None) -> str:
    """
    Format a UTC timestamp in user's local time.

    Args:
        utc_timestamp: ISO format timestamp
        fmt: Output format (default: "YYYY-MM-DD HH:MM")
        user_tz: User's timezone

    Returns:
        Formatted datetime string in local time
    """
    _, local_dt = get_canonical_day(utc_timestamp, user_tz)
    if local_dt:
        return local_dt.strftime(fmt)
    # Fallback: return the date only
    return utc_timestamp[:10]


# Alias for backwards compatibility
get_canonical_date = get_canonical_day

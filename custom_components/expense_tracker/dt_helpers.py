"""Timezone-aware date/time helpers shared by services.py and sensor.py.

Centralized here because both call sites need the same two operations
done the same, correct way: normalizing a bare local date string into a
full UTC ISO timestamp for storage, and finding "the start of the current
calendar month" as a UTC instant so it can be compared against those
stored timestamps.
"""
from __future__ import annotations

from datetime import datetime

from homeassistant.util import dt as dt_util


def local_date_string_to_utc_iso(date_str: str) -> str:
    """Convert a bare local date string (e.g. "2026-09-01", exactly what
    HA's `date` selector produces) into a full UTC ISO timestamp
    representing local midnight on that date.

    If `date_str` isn't a bare date (defensive - the `date` selector
    should never produce anything else), it's returned unchanged on the
    assumption it's already a valid ISO timestamp.
    """
    parsed_date = dt_util.parse_date(date_str)
    if parsed_date is None:
        return date_str
    naive_local_midnight = datetime.combine(parsed_date, datetime.min.time())
    # as_local() on a naive datetime tags it as already being in HA's
    # configured local timezone (it does not shift the clock values) -
    # exactly what we want for "midnight, local time, on this date".
    local_midnight = dt_util.as_local(naive_local_midnight)
    return dt_util.as_utc(local_midnight).isoformat()


def start_of_current_month_utc() -> datetime:
    """Return the start (local midnight on the 1st) of the current
    calendar month, as measured in HA's configured local timezone, as a
    UTC-aware datetime."""
    local_now = dt_util.now()
    local_month_start = local_now.replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    return dt_util.as_utc(local_month_start)

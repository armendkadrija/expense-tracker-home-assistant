from homeassistant.util import dt as dt_util

from custom_components.expense_tracker.dt_helpers import (
    local_date_string_to_utc_iso,
    start_of_current_month_utc,
)


async def test_local_date_string_to_utc_iso_uses_configured_local_timezone(hass):
    await hass.config.async_set_time_zone("US/Pacific")

    result = local_date_string_to_utc_iso("2026-09-01")

    # Midnight Sept 1 in US/Pacific (UTC-7 during DST) is 07:00 UTC.
    parsed = dt_util.parse_datetime(result)
    assert parsed is not None
    assert parsed.utcoffset().total_seconds() == 0
    local = dt_util.as_local(parsed)
    assert (local.year, local.month, local.day, local.hour) == (2026, 9, 1, 0)


async def test_local_date_string_to_utc_iso_passthrough_for_non_date_string(hass):
    already_iso = "2026-09-01T10:00:00+00:00"

    assert local_date_string_to_utc_iso(already_iso) == already_iso


async def test_start_of_current_month_utc_matches_local_month_boundary(hass):
    await hass.config.async_set_time_zone("US/Pacific")

    result = start_of_current_month_utc()

    local_result = dt_util.as_local(result)
    local_now = dt_util.now()
    assert local_result == local_now.replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )

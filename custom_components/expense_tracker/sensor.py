"""Sensor platform for the Expense Tracker integration."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .dt_helpers import start_of_current_month_utc
from .runtime import ExpenseTrackerRuntime


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime: ExpenseTrackerRuntime = hass.data[DOMAIN][entry.entry_id]
    total_sensor = ExpenseTrackerTotalSensor(runtime, this_month=False)
    month_sensor = ExpenseTrackerTotalSensor(runtime, this_month=True)
    runtime.sensors = [total_sensor, month_sensor]
    # Initial refresh happens in each sensor's async_added_to_hass(), not
    # here - HA guarantees that lifecycle method runs only after the
    # entity is fully attached (hass/entity_id assigned, state machine
    # ready for async_write_ha_state()). Calling async_refresh()
    # immediately after async_add_entities() used to work only because of
    # an incidental executor-hop timing coincidence, not a guarantee.
    async_add_entities([total_sensor, month_sensor])


def _start_of_month_iso() -> str:
    return start_of_current_month_utc().isoformat()


class ExpenseTrackerTotalSensor(SensorEntity):
    _attr_should_poll = False
    _attr_state_class = SensorStateClass.TOTAL
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_suggested_display_precision = 2

    def __init__(self, runtime: ExpenseTrackerRuntime, this_month: bool) -> None:
        self._runtime = runtime
        self._this_month = this_month
        suffix = "total_this_month" if this_month else "total"
        self._attr_unique_id = f"{DOMAIN}_{suffix}"
        self.entity_id = f"sensor.{DOMAIN}_{suffix}"
        self._attr_name = (
            "Expenses this month" if this_month else "Expenses total"
        )

    @property
    def native_unit_of_measurement(self) -> str | None:
        return self._runtime.hass.config.currency

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        await self.async_refresh()

    async def async_refresh(self) -> None:
        since = _start_of_month_iso() if self._this_month else None
        totals = await self._runtime.async_get_totals(since=since)
        types = await self._runtime.async_list_types()
        self._attr_native_value = totals["total"]
        self._attr_extra_state_attributes = {
            "by_type": totals["by_type"],
            "by_user": totals["by_user"],
            "count": totals["count"],
            "types": dict(types),
        }
        if self._this_month:
            # HA's long-term statistics need last_reset on a state_class
            # 'total' sensor to correctly treat the month boundary as an
            # intentional reset rather than anomalous data.
            self._attr_last_reset = start_of_current_month_utc()
        self.async_write_ha_state()

"""Sensor platform for the Expense Tracker integration."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
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
    async_add_entities([total_sensor, month_sensor])
    await total_sensor.async_refresh()
    await month_sensor.async_refresh()


def _start_of_month_iso() -> str:
    return start_of_current_month_utc().isoformat()


class ExpenseTrackerTotalSensor(SensorEntity):
    _attr_should_poll = False
    _attr_state_class = SensorStateClass.TOTAL

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

    async def async_refresh(self) -> None:
        since = _start_of_month_iso() if self._this_month else None
        totals = await self._runtime.async_get_totals(since=since)
        self._attr_native_value = totals["total"]
        self._attr_extra_state_attributes = {
            "by_type": totals["by_type"],
            "by_user": totals["by_user"],
            "count": totals["count"],
        }
        self.async_write_ha_state()

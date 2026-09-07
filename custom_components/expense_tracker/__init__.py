"""The Expense Tracker integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DB_FILENAME, DOMAIN
from .db import ExpenseDB
from .runtime import ExpenseTrackerRuntime
from .services import async_register_services, async_unregister_services

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    db_path = hass.config.path(DOMAIN, DB_FILENAME)
    db = ExpenseDB(db_path)
    runtime = ExpenseTrackerRuntime(hass, db)
    await runtime.async_initialize()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = runtime
    async_register_services(hass, runtime)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    from .script_sync import async_sync_script

    type_names = [name for name, _icon in await runtime.async_list_types()]
    await async_sync_script(hass, type_names)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        async_unregister_services(hass)
    return unload_ok

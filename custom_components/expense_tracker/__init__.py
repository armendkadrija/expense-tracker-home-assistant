"""The Expense Tracker integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceNotFound

from .const import DB_FILENAME, DOMAIN
from .db import ExpenseDB
from .runtime import ExpenseTrackerRuntime
from .services import async_register_services, async_unregister_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    db_path = hass.config.path(DOMAIN, DB_FILENAME)
    db = ExpenseDB(db_path)
    runtime = ExpenseTrackerRuntime(hass, db)
    await runtime.async_initialize()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = runtime

    # Sync the add-expense helper script as early as possible, and make
    # it non-fatal. async_sync_script_now() calls the `script`
    # component's public script.reload service, which raises
    # ServiceNotFound if `script` isn't loaded (it's declared as an
    # after_dependency, not a hard dependency, so it may not be loaded
    # yet or may be entirely absent from the user's config). Previously
    # this call happened last, after services were registered and
    # platforms forwarded; an uncaught ServiceNotFound aborted setup with
    # a SETUP_ERROR, and HA does not call async_unload_entry in that
    # case, permanently leaking the just-registered services and
    # platforms. Now a missing `script` component just means the
    # dashboard form won't reflect the latest types until `script` loads
    # and a future add_type/remove_type re-syncs, or the integration
    # reloads -- the data layer and services below still work fine.
    try:
        await runtime.async_sync_script_now()
    except ServiceNotFound:
        _LOGGER.warning(
            "Could not sync the expense_tracker_add_expense script: the "
            "'script' component is not loaded. The dashboard form will "
            "show stale expense types until it is."
        )

    async_register_services(hass, runtime)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        async_unregister_services(hass)
    return unload_ok

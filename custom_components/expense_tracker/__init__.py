"""The Expense Tracker integration."""
from __future__ import annotations

from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CARD_FILES, DB_FILENAME, DOMAIN, STATIC_URL_PREFIX
from .db import ExpenseDB
from .lovelace_setup import async_register_dashboard_resources
from .runtime import ExpenseTrackerRuntime
from .services import async_register_services, async_unregister_services

PLATFORMS = [Platform.SENSOR]

_WWW_DIR = Path(__file__).parent / "www"


async def _async_register_static_files(hass: HomeAssistant) -> None:
    """Serve the dashboard card JS from the integration's own www/
    directory via hass.http.async_register_static_paths -- a verified
    public HA API (homeassistant/components/http/__init__.py). Guarded
    against double-registration on a config entry reload, which the
    underlying aiohttp route table doesn't tolerate cleanly."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get("_static_paths_registered"):
        return
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                f"{STATIC_URL_PREFIX}/{name}", str(_WWW_DIR / name), cache_headers=True
            )
            for name in CARD_FILES
        ]
    )
    domain_data["_static_paths_registered"] = True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    db_path = hass.config.path(DOMAIN, DB_FILENAME)
    db = ExpenseDB(db_path)
    runtime = ExpenseTrackerRuntime(hass, db)
    await runtime.async_initialize()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = runtime
    await _async_register_static_files(hass)
    await async_register_dashboard_resources(hass)

    async_register_services(hass, runtime)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        async_unregister_services(hass)
    return unload_ok

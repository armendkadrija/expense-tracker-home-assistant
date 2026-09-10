"""Best-effort automatic registration of this integration's dashboard
resources with Home Assistant's Lovelace frontend.

Verified against the installed HA source
(homeassistant/components/lovelace/__init__.py, dashboard.py, resources.py):
`hass.data[LOVELACE_DATA].resources` is a real, reachable
`ResourceStorageCollection`, built on the public
`homeassistant.helpers.collection.DictStorageCollection` base class -- so
registering resources in-process is achievable, not a hack.

Creating an entirely NEW dashboard is NOT achievable the same way: the
`DashboardsCollection` that owns dashboard creation is a local variable
inside lovelace's own `async_setup()` -- never stored on `hass.data` or
exposed anywhere else reachable. There is no in-process reference to it.
That part stays a documented manual step (see README's "Dashboard setup").

`hass.data[LOVELACE_DATA]` itself is the `lovelace` component's own
internal data structure, not part of `homeassistant.helpers.*` (HA's
actual versioned, deprecation-protected integration-author surface) --
its shape isn't a guaranteed contract the way a `helpers.*` call is. So
this whole thing is wrapped defensively: any failure here is logged and
swallowed, never allowed to break integration setup.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from homeassistant.core import HomeAssistant

from .const import CARD_FILES, STATIC_URL_PREFIX

_LOGGER = logging.getLogger(__name__)

_MANIFEST_PATH = Path(__file__).parent / "manifest.json"


def _read_integration_version() -> str:
    """Read this integration's own version straight from manifest.json on
    disk, every call -- deliberately NOT via homeassistant.loader's
    async_get_integration.

    Blocking file I/O -- callers MUST run this via
    hass.async_add_executor_job, never directly on the event loop. (Shipped
    once without that: HA's blocking-call detector caught it live --
    `.open()` inside `async_register_dashboard_resources`, a hard rule
    this project otherwise holds everywhere else, missed here because this
    function reads like a cheap in-memory lookup rather than file I/O.)

    That loader API caches the parsed Integration object (including its
    manifest) in hass.data for the lifetime of the HA process
    (homeassistant/loader.py's async_get_integrations, keyed by domain).
    A config-entry reload re-runs this module's setup code but does NOT
    clear that cache -- confirmed live: after `homeassistant.
    reload_config_entry` following a version bump, this returned the
    OLD version, and the resource URL below stayed on the stale
    ?v=<old> for anyone hitting a cache that already had it. Only a full
    HA restart clears hass.data. Reading the file directly sidesteps that
    entirely: HACS writes the new manifest.json to disk immediately on
    download, so this always reflects what's actually installed, restart
    or not.
    """
    try:
        with _MANIFEST_PATH.open(encoding="utf-8") as handle:
            return str(json.load(handle)["version"])
    except (OSError, ValueError, KeyError):
        _LOGGER.exception("Could not read own manifest.json for version info")
        return "0"


async def async_register_dashboard_resources(hass: HomeAssistant) -> None:
    """Register this integration's card JS as Lovelace resources, creating
    or updating them as needed. Idempotent and never raises -- worst case,
    the user adds the resources manually per the README.

    Each URL carries a `?v=<integration version>` query string. This isn't
    cosmetic: the static files are served with a 31-day Cache-Control (see
    __init__.py's _async_register_static_files), and on deployments that
    additionally sit behind a CDN, that header gets honored at the edge --
    verified live on this project's own instance (Cloudflare,
    cf-cache-status: HIT serving a stale card file after a version bump,
    even past a hard client-side cache-bypass fetch). Changing the URL on
    every version is the standard fix: a stale cached response just stops
    being referenced by anything, instead of needing an edge purge.

    If more than one existing resource matches a given card file (which
    can happen from earlier bugs in this same function, or from a user
    having added one manually before this existed), every run consolidates
    them down to exactly one -- deleting the extras -- rather than leaving
    duplicates to accumulate. Confirmed live: without this, a stale-version
    run (see _read_integration_version's docstring) that found zero
    matches due to an unrelated timing issue created a fresh duplicate
    instead of updating the existing ones.
    """
    try:
        from homeassistant.components.lovelace.const import LOVELACE_DATA

        lovelace_data = hass.data.get(LOVELACE_DATA)
        if lovelace_data is None:
            _LOGGER.debug(
                "Lovelace isn't loaded yet; skipping automatic dashboard "
                "resource registration. Add the resources manually "
                "(see README) if this integration's cards don't load."
            )
            return

        version = await hass.async_add_executor_job(_read_integration_version)

        existing_items = lovelace_data.resources.async_items() or []
        for name in CARD_FILES:
            base_url = f"{STATIC_URL_PREFIX}/{name}"
            versioned_url = f"{base_url}?v={version}"
            matches = [
                item
                for item in existing_items
                if item.get("url", "").split("?", 1)[0] == base_url
            ]
            if not matches:
                await lovelace_data.resources.async_create_item(
                    {"res_type": "module", "url": versioned_url}
                )
                continue
            survivor, *extras = matches
            for extra in extras:
                await lovelace_data.resources.async_delete_item(extra["id"])
            if survivor.get("url") != versioned_url:
                await lovelace_data.resources.async_update_item(
                    survivor["id"], {"url": versioned_url}
                )
    except Exception:  # noqa: BLE001 - best-effort only, see module docstring
        _LOGGER.exception(
            "Could not automatically register dashboard resources. Add "
            "them manually (see README) if this integration's cards "
            "don't load."
        )

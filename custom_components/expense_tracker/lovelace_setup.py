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

import logging

from homeassistant.core import HomeAssistant

from .const import CARD_FILES, STATIC_URL_PREFIX

_LOGGER = logging.getLogger(__name__)


async def async_register_dashboard_resources(hass: HomeAssistant) -> None:
    """Register this integration's card JS as Lovelace resources, if not
    already registered. Idempotent (checked by URL) and never raises --
    worst case, the user adds the two resources manually per the README."""
    try:
        from homeassistant.components.lovelace.const import LOVELACE_DATA

        lovelace_data = hass.data.get(LOVELACE_DATA)
        if lovelace_data is None:
            _LOGGER.debug(
                "Lovelace isn't loaded yet; skipping automatic dashboard "
                "resource registration. Add the two resources manually "
                "(see README) if this integration's cards don't load."
            )
            return

        existing_urls = {
            item.get("url")
            for item in (lovelace_data.resources.async_items() or [])
        }
        for name in CARD_FILES:
            url = f"{STATIC_URL_PREFIX}/{name}"
            if url in existing_urls:
                continue
            await lovelace_data.resources.async_create_item(
                {"res_type": "module", "url": url}
            )
    except Exception:  # noqa: BLE001 - best-effort only, see module docstring
        _LOGGER.exception(
            "Could not automatically register dashboard resources. Add "
            "them manually (see README) if this integration's cards "
            "don't load."
        )

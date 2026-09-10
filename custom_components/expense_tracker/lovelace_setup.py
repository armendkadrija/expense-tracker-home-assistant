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
from homeassistant.loader import async_get_integration

from .const import CARD_FILES, DOMAIN, STATIC_URL_PREFIX

_LOGGER = logging.getLogger(__name__)


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
    `async_get_integration` (homeassistant.loader) is the public API for
    reading our own manifest version at runtime.
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

        integration = await async_get_integration(hass, DOMAIN)
        version = str(integration.version)

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
            for item in matches:
                if item.get("url") != versioned_url:
                    await lovelace_data.resources.async_update_item(
                        item["id"], {"url": versioned_url}
                    )
    except Exception:  # noqa: BLE001 - best-effort only, see module docstring
        _LOGGER.exception(
            "Could not automatically register dashboard resources. Add "
            "them manually (see README) if this integration's cards "
            "don't load."
        )

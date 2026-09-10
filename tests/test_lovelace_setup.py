from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.loader import async_get_integration
from homeassistant.setup import async_setup_component

from custom_components.expense_tracker.const import (
    CARD_FILES,
    DOMAIN,
    STATIC_URL_PREFIX,
)
from custom_components.expense_tracker.lovelace_setup import (
    async_register_dashboard_resources,
)


async def test_setup_entry_registers_dashboard_resources_when_lovelace_loaded(
    hass, tmp_path
):
    assert await async_setup_component(hass, "lovelace", {})
    hass.config.config_dir = str(tmp_path)
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    base_urls = {
        item.get("url", "").split("?", 1)[0]
        for item in hass.data[LOVELACE_DATA].resources.async_items()
    }
    for name in CARD_FILES:
        assert f"{STATIC_URL_PREFIX}/{name}" in base_urls


async def test_registering_resources_twice_does_not_duplicate(hass, tmp_path):
    assert await async_setup_component(hass, "lovelace", {})
    hass.config.config_dir = str(tmp_path)
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    await async_register_dashboard_resources(hass)
    await async_register_dashboard_resources(hass)

    urls = [
        item.get("url")
        for item in hass.data[LOVELACE_DATA].resources.async_items()
        if item.get("url", "").startswith(STATIC_URL_PREFIX)
    ]
    assert len(urls) == len(CARD_FILES)


async def test_resource_url_carries_integration_version(hass, tmp_path):
    """Each resource URL must be cache-busted with the integration's own
    version -- see lovelace_setup.py's docstring for why this matters
    (verified live: a CDN in front of a real deployment served a stale
    card file for a bare, unversioned URL past a version bump)."""
    assert await async_setup_component(hass, "lovelace", {})
    hass.config.config_dir = str(tmp_path)
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    integration = await async_get_integration(hass, DOMAIN)
    expected_suffix = f"?v={integration.version}"

    matched_any = False
    for item in hass.data[LOVELACE_DATA].resources.async_items():
        if item.get("url", "").split("?", 1)[0].startswith(STATIC_URL_PREFIX):
            matched_any = True
            assert item["url"].endswith(expected_suffix)
    assert matched_any


async def test_reregistering_converges_stale_versioned_url_without_duplicating(
    hass, tmp_path
):
    """A resource left registered with a previous release's ?v= (or none
    at all) must be updated in place on the next setup, not duplicated --
    this in-place update is what actually defeats the stale-cache problem,
    since the URL only changes for people if the existing resource entry
    is rewritten to point at it."""
    assert await async_setup_component(hass, "lovelace", {})
    hass.config.config_dir = str(tmp_path)
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    resources = hass.data[LOVELACE_DATA].resources
    name = CARD_FILES[0]
    base_url = f"{STATIC_URL_PREFIX}/{name}"
    item = next(
        i
        for i in resources.async_items()
        if i.get("url", "").split("?", 1)[0] == base_url
    )
    await resources.async_update_item(
        item["id"], {"url": f"{base_url}?v=0.0.0-stale"}
    )

    await async_register_dashboard_resources(hass)

    matches = [
        i
        for i in resources.async_items()
        if i.get("url", "").split("?", 1)[0] == base_url
    ]
    assert len(matches) == 1
    assert matches[0]["id"] == item["id"]
    assert "0.0.0-stale" not in matches[0]["url"]


async def test_setup_entry_survives_lovelace_not_loaded(hass, tmp_path):
    """lovelace isn't set up at all in this test -- setup must not raise."""
    hass.config.config_dir = str(tmp_path)
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state.value == "loaded"
